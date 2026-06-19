"""Gemini provider for the report pipeline — alternate to the default Anthropic
provider (set LLM_PROVIDER=gemini and LLM_MODEL=gemini-2.5-pro).

generate()/generate_text() return raw JSON text; pipeline/llm.py orchestrates
validation, lint/repair, and model fallback.
"""
from __future__ import annotations

from google import genai
from google.genai import types

from config import settings

_client: "genai.Client | None" = None


def _c() -> "genai.Client":
    global _client
    if _client is None:
        if settings.GOOGLE_GEMINI_BASE_URL:
            _client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(base_url=settings.GOOGLE_GEMINI_BASE_URL))
        else:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate(system_prompt: str, image_jpegs: list[bytes], user_text: str, model: str) -> str:
    parts: list = [types.Part.from_bytes(data=j, mime_type="image/jpeg") for j in image_jpegs]
    parts.append(user_text)
    resp = _c().models.generate_content(
        model=model, contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json", temperature=0.5),
    )
    return resp.text or ""


def generate_text(prompt: str, model: str) -> str:
    resp = _c().models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0.2),
    )
    return resp.text or ""
