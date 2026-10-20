from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Report:
    id: str
    description: str
    category: str
    landmark: str | None
    status: str
    summary: str | None
    priority_hint: str | None
    created_at: str
    updated_at: str
    resolved_at: str | None
    resolution_note: str | None
    demo_data_flag: bool
    analysis_source: str
    title: str | None = None
    area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    reported_category: str | None = None


@dataclass(frozen=True, slots=True)
class ReportEvent:
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


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    id: str
    description: str
    category: str
    summary: str | None


@dataclass(frozen=True, slots=True)
class DuplicateSuggestion:
    id: str
    summary: str
    match_reason: str


@dataclass(frozen=True, slots=True)
class RuleAnalysis:
    summary: str
    category_suggestion: str | None
    priority_hint: str | None
    missing_fields: list[str]
