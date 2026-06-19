"""Report generation orchestrator (provider-agnostic).

generate_report(): images + context -> a validated report. Tries LLM_MODEL, then
LLM_FALLBACK_MODEL; invalid JSON / API error / refusal counts as a failed attempt
(Golos spec §7.2). After a valid parse it runs the per-locale linter + repair loop.
The provider is selected by settings.LLM_PROVIDER (anthropic | gemini); each provider
module exposes generate() and generate_text().
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from config import settings
from pipeline.images import prepare_image
from pipeline.lint import find_violations
from pipeline.prompt import (PROMPT_VERSION, build_user_prompt, repair_instruction,
                             system_prompt)
from pipeline.schema import InsufficientReport, Report, validate_report


class ReportGenerationError(Exception):
    """All attempts (across primary + fallback model) exhausted."""

    def __init__(self, message: str, attempts_log: list[str]):
        super().__init__(message)
        self.attempts_log = attempts_log


@dataclass
class GenerationResult:
    report: "Report | InsufficientReport"
    raw_json_text: str
    prompt_version: str = PROMPT_VERSION
    provider: str = settings.LLM_PROVIDER
    model: str = ""
    locale: str = settings.DEFAULT_LOCALE
    attempts_used: int = 1
    repair_rounds: int = 0
    lint_hits_left: int = 0
    image_jpegs: list[bytes] = field(default_factory=list)


def _provider():
    if settings.LLM_PROVIDER == "gemini":
        from pipeline import gemini as p
    else:
        from pipeline import anthropic_llm as p
    return p


def _models() -> list[str]:
    models = [settings.LLM_MODEL]
    if settings.LLM_FALLBACK_MODEL and settings.LLM_FALLBACK_MODEL not in models:
        models.append(settings.LLM_FALLBACK_MODEL)
    return models


def _strip_markdown_fence(text: str) -> str:
    """The model sometimes wraps JSON in ```json ... ``` despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _repair(provider, report_dict: dict, violations: list[dict], locale: str, model: str) -> dict:
    issues = "\n".join(
        f"- {v['where']}: \"{v['match']}\" - {v['why']} (context: ...{v['context']}...)"
        for v in violations
    )
    prompt = (f"{repair_instruction(locale)}\n\nViolations found:\n{issues}\n\n"
              f"Report JSON:\n{json.dumps(report_dict, ensure_ascii=False)}")
    return json.loads(_strip_markdown_fence(provider.generate_text(prompt, model)))


def generate_report(image_paths: list[Path], contexts: list[str] | str,
                    common_context: str = "", locale: str = settings.DEFAULT_LOCALE,
                    max_attempts: int | None = None, raw_dump_dir: Path | None = None,
                    system_prompt_override: str | None = None,
                    enable_lint: bool = True) -> GenerationResult:
    """contexts: per-drawing stories (image order); a single string = one for all."""
    provider = _provider()
    max_attempts = max_attempts or settings.LLM_MAX_ATTEMPTS

    if isinstance(contexts, str):
        contexts = [contexts] * len(image_paths) if len(image_paths) > 1 else [contexts]
    if len(contexts) != len(image_paths):
        raise ValueError(f"contexts ({len(contexts)}) != images ({len(image_paths)})")

    jpegs = [prepare_image(p) for p in image_paths]
    sys_prompt = system_prompt_override or system_prompt(locale)
    user_text = build_user_prompt(contexts, common_context, locale)

    attempts_log: list[str] = []
    attempt_no = 0
    for model in _models():
        for attempt in range(1, max_attempts + 1):
            attempt_no += 1
            try:
                raw = provider.generate(sys_prompt, jpegs, user_text, model)
                if raw_dump_dir is not None:
                    raw_dump_dir.mkdir(parents=True, exist_ok=True)
                    (raw_dump_dir / f"attempt_{attempt_no}_{model}.txt").write_text(raw, encoding="utf-8")
                report = validate_report(json.loads(_strip_markdown_fence(raw)))

                repair_rounds = 0
                violations: list[dict] = []
                if enable_lint and isinstance(report, Report):
                    violations = find_violations(report.model_dump(), locale)
                    while violations and repair_rounds < 2:
                        repair_rounds += 1
                        try:
                            fixed = _repair(provider, report.model_dump(), violations, locale, model)
                            candidate = validate_report(fixed)
                            if isinstance(candidate, Report):
                                new_violations = find_violations(candidate.model_dump(), locale)
                                if len(new_violations) < len(violations):
                                    report, violations = candidate, new_violations
                                    continue
                        except (json.JSONDecodeError, ValidationError):
                            pass  # a failed repair never spoils an already-valid report
                        break

                return GenerationResult(
                    report=report, raw_json_text=raw, provider=settings.LLM_PROVIDER,
                    model=model, locale=locale, attempts_used=attempt_no, image_jpegs=jpegs,
                    repair_rounds=repair_rounds, lint_hits_left=len(violations))
            except (json.JSONDecodeError, ValidationError) as e:
                attempts_log.append(f"attempt {attempt_no} [{model}]: invalid output: {e}")
            except Exception as e:  # network / API / refusal — also a failed attempt
                attempts_log.append(f"attempt {attempt_no} [{model}]: {type(e).__name__}: {e}")
            if attempt < max_attempts:
                time.sleep(min(5 * attempt, 30))

    raise ReportGenerationError(
        f"LLM ({settings.LLM_PROVIDER}): all attempts exhausted across {_models()}",
        attempts_log)
