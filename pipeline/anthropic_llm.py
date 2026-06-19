"""Anthropic (Claude) provider for the report pipeline — the default provider.

Same role as the Gemini provider: turn images + prompts into raw JSON text.
Orchestration (attempts, JSON validation, lint/repair, model fallback) lives in
pipeline/llm.py. No sampling params are sent, so the same code works across Sonnet,
Haiku, and (future) Opus/Fable models selected via LLM_MODEL.
"""
from __future__ import annotations

import base64

import anthropic

from config import settings

_client: "anthropic.Anthropic | None" = None
_MAX_TOKENS = 16000


class LLMRefusal(RuntimeError):
    """The model declined the request (stop_reason == 'refusal')."""


def _c() -> "anthropic.Anthropic":
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _text(resp) -> str:
    if getattr(resp, "stop_reason", None) == "refusal":
        raise LLMRefusal("model refused the request")
    out = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    if not out.strip():
        raise RuntimeError("empty response from model")
    return out


def generate(system_prompt: str, image_jpegs: list[bytes], user_text: str, model: str) -> str:
    """Images + context -> raw JSON text (the report)."""
    blocks: list = [
        {"type": "image",
         "source": {"type": "base64", "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(j).decode("ascii")}}
        for j in image_jpegs
    ]
    blocks.append({"type": "text", "text": user_text})
    resp = _c().messages.create(
        model=model, max_tokens=_MAX_TOKENS, system=system_prompt,
        messages=[{"role": "user", "content": blocks}],
    )
    return _text(resp)


def generate_text(prompt: str, model: str) -> str:
    """Text-only call (the lint repair pass)."""
    resp = _c().messages.create(
        model=model, max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text(resp)
