"""Gemini call: images + context -> validated report JSON.

Resilience (Golos spec §7.2): up to 5 attempts, invalid JSON = a failed attempt;
all raw responses are saved for debugging. Locale flows through the whole call:
system prompt, user prompt, linter, and repair instruction are all per-locale.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError

from config import settings
from pipeline.images import prepare_image
from pipeline.lint import find_violations
from pipeline.prompt import (PROMPT_VERSION, build_user_prompt, repair_instruction,
                             system_prompt)
from pipeline.schema import InsufficientReport, Report, validate_report


class ReportGenerationError(Exception):
    """All attempts exhausted. attempts_log - list of per-attempt errors."""

    def __init__(self, message: str, attempts_log: list[str]):
        super().__init__(message)
        self.attempts_log = attempts_log


@dataclass
class GenerationResult:
    report: Report | InsufficientReport
    raw_json_text: str          # raw model response - must be stored (spec §5)
    prompt_version: str = PROMPT_VERSION
    model: str = settings.GEMINI_MODEL
    locale: str = settings.DEFAULT_LOCALE
    attempts_used: int = 1
    repair_rounds: int = 0      # how many linter repair passes were needed
    lint_hits_left: int = 0     # violations left after repair (0 = clean)
    image_jpegs: list[bytes] = field(default_factory=list)  # prepared images


def _make_client() -> "genai.Client":
    if settings.GOOGLE_GEMINI_BASE_URL:
        return genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(base_url=settings.GOOGLE_GEMINI_BASE_URL),
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _repair_report(client: "genai.Client", report_dict: dict,
                   violations: list[dict], locale: str) -> dict:
    """Text-only repair call: rewrite the spots the linter flagged."""
    issues = "\n".join(
        f"- {v['where']}: \"{v['match']}\" - {v['why']} (context: ...{v['context']}...)"
        for v in violations
    )
    prompt = (f"{repair_instruction(locale)}\n\nViolations found:\n{issues}\n\n"
              f"Report JSON:\n{json.dumps(report_dict, ensure_ascii=False)}")
    resp = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0.2,
        ),
    )
    return json.loads(_strip_markdown_fence(resp.text or ""))


def _strip_markdown_fence(text: str) -> str:
    """The model sometimes wraps JSON in ```json ... ``` despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def generate_report(image_paths: list[Path], contexts: list[str] | str,
                    common_context: str = "", locale: str = settings.DEFAULT_LOCALE,
                    max_attempts: int = settings.GEMINI_MAX_ATTEMPTS,
                    raw_dump_dir: Path | None = None,
                    system_prompt_override: str | None = None,
                    enable_lint: bool = True) -> GenerationResult:
    """contexts: list of per-drawing stories (in image_paths order);
    a single string = one context for all drawings (legacy/single drawing).

    system_prompt_override / enable_lint are extension points for the prompt lab
    (scripts/prompt_lab.py). Default = production behavior unchanged."""
    client = _make_client()

    if isinstance(contexts, str):
        contexts = [contexts] * len(image_paths) if len(image_paths) > 1 else [contexts]
    if len(contexts) != len(image_paths):
        raise ValueError(f"contexts ({len(contexts)}) != images ({len(image_paths)})")

    jpegs = [prepare_image(p) for p in image_paths]
    parts: list = [types.Part.from_bytes(data=j, mime_type="image/jpeg") for j in jpegs]
    parts.append(build_user_prompt(contexts, common_context, locale))

    config = types.GenerateContentConfig(
        system_instruction=system_prompt_override or system_prompt(locale),
        response_mime_type="application/json",
        temperature=0.5,
    )

    attempts_log: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=parts, config=config,
            )
            raw = resp.text or ""
            if raw_dump_dir is not None:
                raw_dump_dir.mkdir(parents=True, exist_ok=True)
                (raw_dump_dir / f"attempt_{attempt}.txt").write_text(raw, encoding="utf-8")
            data = json.loads(_strip_markdown_fence(raw))
            report = validate_report(data)

            # linguistic linter + repair passes (not for insufficient)
            repair_rounds = 0
            violations: list[dict] = []
            if enable_lint and isinstance(report, Report):
                violations = find_violations(report.model_dump(), locale)
                while violations and repair_rounds < 2:
                    repair_rounds += 1
                    try:
                        fixed = _repair_report(client, report.model_dump(), violations, locale)
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
                report=report, raw_json_text=raw, locale=locale,
                attempts_used=attempt, image_jpegs=jpegs,
                repair_rounds=repair_rounds, lint_hits_left=len(violations),
            )
        except (json.JSONDecodeError, ValidationError) as e:
            attempts_log.append(f"attempt {attempt}: invalid output: {e}")
        except Exception as e:  # network/API errors - also a failed attempt
            attempts_log.append(f"attempt {attempt}: {type(e).__name__}: {e}")
        if attempt < max_attempts:
            time.sleep(min(5 * attempt, 30))

    raise ReportGenerationError(
        f"Gemini: {max_attempts} attempts exhausted", attempts_log,
    )
