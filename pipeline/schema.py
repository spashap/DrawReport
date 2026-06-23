"""Report JSON contract (philosophy 2.3 — portrait of the child as a person).

The model returns DATA; the template owns all presentation. Invalid JSON from the
LLM = a failed attempt - so validation is strict. Language-neutral: the same
structure for every locale; values come back in the report's language.

v2.3 (mirrors Golos v4.0): personality-led directions lead, drawing skills support.
Added about_child (narrative portrait — the heart), split recommendations
(understanding/connecting with the child vs creative activities), specialists
(a type of specialist as an "if you'd like to go deeper" RESOURCE, never alarm).
US recalibration: the prompt keeps emotional/zone-3 reading light + always framed.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# 7 directions (4 personality-led lead + 3 skill-support); 7-8 accepted if zone 2 expands.
DIMENSIONS_MIN = 7
DIMENSIONS_MAX = 8


class Child(BaseModel):
    name: str = Field(min_length=1)
    age_display: str = Field(min_length=1)  # "5 years 6 months"


class Dimension(BaseModel):
    key: str = Field(min_length=1)            # "world_and_themes", ...
    title: str = Field(min_length=1)          # "World & themes"
    score: int = Field(ge=1, le=10)
    observation: str = Field(min_length=1)    # tied to concrete visible details
    research_note: str = ""                   # general reference to research
    activities: list[str] = Field(default_factory=list)


class DevelopmentDirection(BaseModel):
    """Optional "where to grow the child's strengths" block - life-wide, not a prediction."""
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Specialist(BaseModel):
    """A type/area of specialist as a useful "if you'd like to go deeper" resource,
    NOT an alarm. Optional block; must include a non-art option when content warrants."""
    area: str = Field(min_length=1)    # e.g. "a child psychologist who works with projective methods"
    reason: str = Field(min_length=1)  # the visible detail / direction it springs from


class Report(BaseModel):
    child: Child
    context_summary: str = ""
    introduction: str = Field(min_length=1)
    about_child: str = Field(min_length=1)    # narrative portrait of the child as a person (the heart)
    dimensions: list[Dimension]
    # recommendations split: ~half about understanding/connecting with the child, ~half creative activities
    understanding_recommendations: list[str] = Field(default_factory=list)
    art_recommendations: list[str] = Field(default_factory=list)
    specialists: list[Specialist] | None = None
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
