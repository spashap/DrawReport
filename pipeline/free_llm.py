"""Generation of the FREE analysis of one drawing (provider-agnostic orchestrator).

Separate from pipeline/llm.py for three reasons: a different schema (validate_free rather
than validate_report), a different linter (free_lint rather than lint) and a different
repair instruction - the paid one is written about about_child and seven dimensions and is
actively harmful on a short analysis (see the header of free_lint.py). The paid path is
NOT touched by this module.

The provider modules (anthropic_llm / gemini) are reused as-is: they already expose
generate() and generate_text() and send no sampling parameters, so the same code works
across models selected by FREE_LLM_MODEL.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from config import settings
from pipeline.free_lint import (FREE_REPAIR_INSTRUCTION, can_downgrade,
                                drop_hypothesis, find_free_violations)
from pipeline.free_prompt import (CONCERNS_WITHOUT_CORRELATE, FREE_PROMPT_VERSION,
                                  FREE_SYSTEM_PROMPT, build_free_user_prompt)
from pipeline.free_schema import FreeAnalysis, FreeInsufficient, validate_free
from pipeline.images import prepare_image

log = logging.getLogger("free_llm")


class FreeGenerationError(Exception):
    """Every attempt exhausted. attempts_log holds the per-attempt errors."""

    def __init__(self, message: str, attempts_log: list[str]):
        super().__init__(message)
        self.attempts_log = attempts_log


@dataclass
class FreeResult:
    analysis: "FreeAnalysis | FreeInsufficient"
    raw_json_text: str
    prompt_version: str = FREE_PROMPT_VERSION
    provider: str = settings.LLM_PROVIDER
    model: str = ""
    locale: str = settings.DEFAULT_LOCALE
    attempts_used: int = 1
    repair_rounds: int = 0
    lint_hits_left: int = 0
    hypothesis_dropped: bool = False   # the downgrade fired instead of a failure
    elapsed_s: float = 0.0
    image_jpeg: bytes = b""
    lint_hits: list[dict] = field(default_factory=list)


def _provider():
    if settings.LLM_PROVIDER == "gemini":
        from pipeline import gemini as p
    else:
        from pipeline import anthropic_llm as p
    return p


def _strip_markdown_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _repair(provider, data: dict, violations: list[dict], model: str) -> dict:
    issues = "\n".join(
        f"- {v['where']}: \"{v['match']}\" - {v['why']}" for v in violations
    )
    prompt = (f"{FREE_REPAIR_INSTRUCTION}\n\nViolations found:\n{issues}\n\n"
              f"Analysis JSON:\n{json.dumps(data, ensure_ascii=False)}")
    return json.loads(_strip_markdown_fence(provider.generate_text(prompt, model)))


def generate_free_analysis(image_path: Path, *, child_name: str, age: int,
                           address_form: str, concern_key: str,
                           age_band_label: str = "",
                           duration_label: str = "", parent_text: str = "",
                           locale: str = settings.DEFAULT_LOCALE,
                           max_attempts: int | None = None,
                           raw_dump_dir: Path | None = None,
                           system_prompt_override: str | None = None,
                           enable_lint: bool = True) -> FreeResult:
    """One drawing -> a validated, lint-clean free analysis."""
    provider = _provider()
    model = settings.FREE_LLM_MODEL
    max_attempts = max_attempts or settings.FREE_MAX_ATTEMPTS

    jpeg = prepare_image(image_path)
    user_prompt = build_free_user_prompt(
        child_name=child_name, age=age, address_form=address_form,
        age_band_label=age_band_label,
        concern_key=concern_key, duration_label=duration_label,
        parent_text=parent_text)
    sys_prompt = system_prompt_override or FREE_SYSTEM_PROMPT

    log.info("free: ready (model=%s, prompt v%s, concern=%s, lint=%s)",
             model, FREE_PROMPT_VERSION, concern_key, enable_lint)

    attempts_log: list[str] = []
    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            log.info("free: attempt %d/%d ...", attempt, max_attempts)
            raw = provider.generate(sys_prompt, [jpeg], user_prompt, model)
            elapsed = time.time() - t0
            log.info("free: attempt %d <- %.1fs, %d chars", attempt, elapsed, len(raw))
            if raw_dump_dir is not None:
                raw_dump_dir.mkdir(parents=True, exist_ok=True)
                (raw_dump_dir / f"attempt_{attempt}.txt").write_text(raw, encoding="utf-8")

            analysis = validate_free(json.loads(_strip_markdown_fence(raw)))
            if isinstance(analysis, FreeInsufficient):
                log.info("free: insufficient (%s)", analysis.reason_key)
                return FreeResult(analysis=analysis, raw_json_text=raw, model=model,
                                  locale=locale, attempts_used=attempt,
                                  elapsed_s=elapsed, image_jpeg=jpeg)

            # Concerns for which a correlate on one page does not physically exist. The
            # prompt asks for null, but we backstop it here: a "true just in case" is
            # confident garbage in the data, and it would also switch on the mismatch
            # paragraph falsely.
            if concern_key in CONCERNS_WITHOUT_CORRELATE:
                analysis = analysis.model_copy(update={
                    "concern_correlate_visible": None, "concern_correlate_note": ""})

            repairs = 0
            dropped = False
            hits = find_free_violations(analysis, child_name, locale) if enable_lint else []
            log.info("free: lint found %d violation(s)", len(hits))

            if hits and enable_lint:
                for _ in range(settings.FREE_REPAIR_ROUNDS):
                    repairs += 1
                    try:
                        fixed = _repair(provider, analysis.model_dump(), hits, model)
                        cand = validate_free(fixed)
                        if isinstance(cand, FreeAnalysis):
                            new_hits = find_free_violations(cand, child_name, locale)
                            log.info("free: repair %d (%d -> %d)", repairs,
                                     len(hits), len(new_hits))
                            # Accept a candidate that is no WORSE, not only one that is
                            # strictly better. Requiring a strict drop threw away real
                            # progress: a length repair that took 410 words down to 395
                            # still has one violation, so the whole attempt was failed and
                            # regenerated from scratch - paying for a fresh call to redo
                            # work the repair had already partly done.
                            if len(new_hits) <= len(hits):
                                analysis, hits = cand, new_hits
                                if not hits:
                                    break
                                continue
                    except (json.JSONDecodeError, ValidationError) as e:
                        log.info("free: repair produced invalid JSON (%s) - kept original", e)
                    break

                # A downgrade instead of a failure: if only the hypothesis is left, drop it.
                # An analysis with no interpretation is an explicitly lawful outcome, so a
                # shipped, less deep text beats a lost parent.
                if hits and can_downgrade(hits):
                    demoted = drop_hypothesis(analysis, locale)
                    if demoted is not None:
                        after = find_free_violations(demoted, child_name, locale)
                        if not after:
                            analysis, hits, dropped = demoted, after, True
                            log.info("free: hypothesis dropped (downgrade) - clean")

            if hits:
                # We do not hand the parent text with violations: count the attempt failed.
                raise ValueError(f"lint: {len(hits)} violation(s) not cleared "
                                 f"({hits[0]['where']}: {hits[0]['why'][:60]})")

            elapsed = time.time() - t0
            log.info("free: SUCCESS (attempts=%d, repairs=%d, dropped=%s, words=%d)",
                     attempt, repairs, dropped, analysis.word_count())
            return FreeResult(analysis=analysis, raw_json_text=raw, model=model,
                              locale=locale, attempts_used=attempt,
                              repair_rounds=repairs, lint_hits_left=0,
                              hypothesis_dropped=dropped, elapsed_s=elapsed,
                              image_jpeg=jpeg)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            attempts_log.append(f"attempt {attempt}: invalid output: {e}")
            log.warning("free: attempt %d INVALID: %s", attempt, e)
        except Exception as e:      # network / API / timeout - also a failed attempt
            attempts_log.append(f"attempt {attempt}: {type(e).__name__}: {e}")
            log.warning("free: attempt %d ERROR: %s: %s", attempt, type(e).__name__, e)
        if attempt < max_attempts:
            time.sleep(2)           # the parent is waiting on screen - keep the backoff short

    log.error("free: ALL %d attempts exhausted", max_attempts)
    raise FreeGenerationError(f"free: {max_attempts} attempts exhausted", attempts_log)
