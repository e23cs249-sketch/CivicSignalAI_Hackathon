"""Business rules for report status transitions, independent of FastAPI/SQL."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "submitted": frozenset({"acknowledged", "rejected"}),
    "acknowledged": frozenset({"in_progress", "rejected"}),
    "in_progress": frozenset({"resolved", "rejected"}),
    "resolved": frozenset(),
    "rejected": frozenset(),
}

class WorkflowError(Exception): pass
class ReportNotFoundError(WorkflowError): pass
class InvalidTransitionError(WorkflowError): pass
class ConcurrentTransitionError(WorkflowError): pass

@dataclass(frozen=True, slots=True)
class TransitionResult:
    report_id: str
    previous_status: str
    new_status: str
    actor: str
    message: str
    timestamp: str

class WorkflowRepository(Protocol):
    def get_report_status(self, report_id: str) -> str | None: ...
    def transition_status_and_add_event(self, *, report_id: str,
        expected_previous_status: str, new_status: str, actor: str,
        message: str, timestamp: str) -> bool: ...

def allowed_next_statuses(current_status: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(current_status, frozenset())

def transition_report_status(repository: WorkflowRepository, *, report_id: str,
    new_status: str, actor: str = "Team", message: str = "") -> TransitionResult:
    current = repository.get_report_status(report_id)
    if current is None:
        raise ReportNotFoundError(f"Report {report_id} was not found.")
    if new_status not in allowed_next_statuses(current):
        allowed = ", ".join(sorted(allowed_next_statuses(current))) or "none"
        raise InvalidTransitionError(
            f"Cannot transition report from {current!r} to {new_status!r}. Allowed next status(es): {allowed}."
        )
    if new_status in {"resolved", "rejected"} and not message.strip():
        label = "resolution note" if new_status == "resolved" else "rejection reason"
        raise InvalidTransitionError(f"A non-empty {label} is required.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not repository.transition_status_and_add_event(
        report_id=report_id, expected_previous_status=current, new_status=new_status,
        actor=actor, message=message.strip(), timestamp=timestamp):
        raise ConcurrentTransitionError(f"Report {report_id} changed during the transition.")
    return TransitionResult(report_id, current, new_status, actor, message.strip(), timestamp)
