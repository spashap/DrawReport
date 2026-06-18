"""Report JSON contract (Golos spec §7.3 + optional development_directions).

The model returns DATA; the template owns all presentation. Invalid JSON from
Gemini = a failed attempt (spec §7.2) - so validation is strict. Language-neutral:
the same structure for every locale; values come back in the report's language.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# 7 directions; line confidence / planning etc. are folded into observations, so
# 7 (occasionally 8) elements are accepted.
DIMENSIONS_MIN = 7
DIMENSIONS_MAX = 8


class Child(BaseModel):
    name: str = Field(min_length=1)
    age_display: str = Field(min_length=1)  # "5 years 6 months"


class Dimension(BaseModel):
    key: str = Field(min_length=1)            # "creativity", ...
    title: str = Field(min_length=1)          # "Creativity & imagination"
    score: int = Field(ge=1, le=10)
    observation: str = Field(min_length=1)    # tied to concrete visible details
    research_note: str = ""                   # general reference to research
    activities: list[str] = Field(default_factory=list)


class DevelopmentDirection(BaseModel):
    """Optional "possible directions" block - for interest, not a prediction."""
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Report(BaseModel):
    child: Child
    context_summary: str = ""
    introduction: str = Field(min_length=1)
    dimensions: list[Dimension]
    recommendations: list[str] = Field(default_factory=list)
    development_directions: list[DevelopmentDirection] | None = None
    conclusion: str = Field(min_length=1)
    insufficient_input: bool = False
    insufficient_reason: str | None = None

    @field_validator("dimensions")
    @classmethod
    def _dimensions_count(cls, v: list[Dimension]) -> list[Dimension]:
        if not (DIMENSIONS_MIN <= len(v) <= DIMENSIONS_MAX):
            raise ValueError(
                f"dimensions: expected {DIMENSIONS_MIN}-{DIMENSIONS_MAX}, got {len(v)}"
            )
        return v


class InsufficientReport(BaseModel):
    """When insufficient_input=true the rest may be absent - no report is rendered."""
    insufficient_input: bool
    insufficient_reason: str = Field(min_length=1)


def validate_report(data: dict) -> Report | InsufficientReport:
    """Validate raw JSON from Gemini. Raises pydantic.ValidationError."""
    if data.get("insufficient_input"):
        return InsufficientReport.model_validate(data)
    return Report.model_validate(data)
