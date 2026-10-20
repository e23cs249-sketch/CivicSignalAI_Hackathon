from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.labels import Category


PriorityHint = Literal["low", "medium", "high"]
AnalysisSource = Literal["rule_based", "unavailable"]


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    category: Category
    area: str | None = Field(default=None, max_length=120)
    landmark: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_confirmed: bool = False

    @field_validator("landmark", mode="before")
    @classmethod
    def blank_landmark_to_null(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_coordinates(self) -> "ReportInput":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")
        if self.latitude is not None and not self.location_confirmed:
            raise ValueError("Confirm the selected map location before submitting.")
        return self


class DuplicateSuggestionResponse(BaseModel):
    id: str
    summary: str
    match_reason: str


class PreviewResponse(BaseModel):
    source: Literal["rule_based"]
    summary: str
    category_suggestion: Category | None
    priority_hint: PriorityHint | None
    missing_fields: list[str]
    duplicate_suggestions: list[DuplicateSuggestionResponse]


class TimelineEventResponse(BaseModel):
    id: str
    report_id: str
    event_type: str
    actor_type: str
    actor_name: str
    message: str
    status_from: str | None
    status_to: str | None
    evidence_note: str | None
    created_at: str


class ReportCreateResponse(BaseModel):
    id: str
    title: str | None = None
    description: str
    category: Category
    area: str | None = None
    landmark: str | None
    latitude: float | None = None
    longitude: float | None = None
    status: Literal["submitted"]
    summary: str | None
    priority_hint: PriorityHint | None
    analysis_source: AnalysisSource
    analysis_warning: str | None = None
    demo_data_flag: bool
    created_at: str
    updated_at: str
    resolved_at: str | None
    resolution_note: str | None
    timeline: list[TimelineEventResponse]
