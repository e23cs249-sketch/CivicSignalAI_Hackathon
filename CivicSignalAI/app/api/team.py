"""Team workflow and citizen tracking endpoints backed by shared SQLite data."""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app import database
from app.api.auth import current_citizen_user, current_team_user, require_same_origin, require_team_user
from app.services.workflow import (
    ConcurrentTransitionError, InvalidTransitionError, ReportNotFoundError,
    transition_report_status,
)
from app.services.media import MAX_IMAGE_COUNT, validate_and_store_upload

router = APIRouter(tags=["team", "tracking"])
Status = Literal["submitted", "acknowledged", "under_review", "in_progress", "resolved", "rejected"]

class StatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Status
    message: str = Field(default="", max_length=1000)

class SQLiteWorkflowRepository:
    def get_report_status(self, report_id: str) -> str | None:
        report = database.get_report(report_id)
        return str(report["status"]) if report else None

    def transition_status_and_add_event(self, **kwargs) -> bool:
        return database.transition_status_and_add_event(**kwargs)

@router.get("/api/reports")
def list_team_reports(_: dict[str, str] = Depends(require_team_user)) -> dict[str, object]:
    try:
        return {"reports": database.list_reports()}
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Report database is unavailable.") from None

@router.patch("/api/team/reports/{report_id}/status")
@router.patch("/api/reports/{report_id}/status", include_in_schema=False)
def update_team_report_status(
    report_id: str,
    payload: StatusUpdateRequest,
    request: Request,
    team_user: dict[str, str] = Depends(require_team_user),
) -> dict[str, object]:
    require_same_origin(request)
    if not report_id.strip() or len(report_id) > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_report_id", "message": "Invalid report ID."})
    try:
        result = transition_report_status(
            SQLiteWorkflowRepository(), report_id=report_id,
            new_status="acknowledged" if payload.status == "under_review" else payload.status,
            actor=team_user["email"], message=payload.message,
        )
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": str(exc)}) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_transition", "message": str(exc)}) from exc
    except ConcurrentTransitionError as exc:
        raise HTTPException(status_code=409, detail={"code": "concurrent_transition", "message": str(exc)}) from exc
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Report database is unavailable.") from None
    return {
        "report_id": result.report_id,
        "status": result.new_status,
        "message": "Report status updated successfully.",
    }


@router.post("/api/team/reports/{report_id}/updates")
async def add_team_report_update(
    report_id: str,
    request: Request,
    status: str | None = Form(default=None),
    message: str = Form(default="", max_length=1000),
    files: list[UploadFile] = File(default=[]),
    team_user: dict[str, str] = Depends(require_team_user),
) -> dict[str, object]:
    require_same_origin(request)
    status = "acknowledged" if status == "under_review" else status
    allowed = {"submitted", "acknowledged", "in_progress", "resolved", "rejected"}
    if status is not None and status not in allowed:
        raise HTTPException(status_code=422, detail="Choose a valid report status.")
    if len(files) > MAX_IMAGE_COUNT:
        raise HTTPException(status_code=400, detail=f"Choose no more than {MAX_IMAGE_COUNT} photos.")
    if not message.strip() and not files and status is None:
        raise HTTPException(status_code=400, detail="Add a note, photo, or status change.")

    stored: list[dict[str, str]] = []
    try:
        for upload in files:
            stored.append(await validate_and_store_upload(upload))
        items = [
            {
                "id": item["id"],
                "storage_path": item["path"],
                "content_type": item["content_type"],
                "size_bytes": item["size"],
            }
            for item in stored
        ]
        result, event_id = database.add_team_update(
            report_id=report_id,
            status=status,
            message=message.strip(),
            actor=team_user["email"],
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            media_items=items,
        )
        if result == "missing":
            raise HTTPException(status_code=404, detail="Report was not found.")
        if result == "invalid":
            raise HTTPException(status_code=409, detail=f"This report cannot move from {event_id} to {status}.")
        if result == "note_required":
            raise HTTPException(status_code=409, detail="A resolution note is required.")
        if result == "reason_required":
            raise HTTPException(status_code=409, detail="A rejection reason is required.")
        return {"report_id": report_id, "event_id": event_id, "message": "Report update saved."}
    except HTTPException:
        for item in stored:
            Path(item["path"]).unlink(missing_ok=True)
        raise
    except Exception:
        for item in stored:
            Path(item["path"]).unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Report update could not be saved.") from None
    finally:
        for upload in files:
            await upload.close()

@router.get("/api/reports/{report_id}/tracking")
def get_report_tracking(report_id: str, request: Request) -> dict[str, object]:
    if not report_id.strip() or len(report_id) > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_report_id", "message": "Invalid report ID."})
    team_user = current_team_user(request)
    citizen_user = current_citizen_user(request)
    if team_user is None and citizen_user is None:
        raise HTTPException(status_code=401, detail="Authentication is required to track reports.")
    try:
        report = database.get_report(report_id)
        if report is None:
            raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": "Report was not found."})
        if team_user is None and database.get_report_citizen_id(report_id) != citizen_user["id"]:
            raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": "Report was not found."})
        media = database.get_report_media(report_id)
        return {
            "report": report,
            "timeline": database.get_report_events(report_id),
            "images": [
                {
                    "id": item["id"],
                    "event_id": item["event_id"],
                    "uploader_role": item["uploader_role"],
                    "media_type": item["media_type"],
                    "content_type": item["content_type"],
                    "size_bytes": item["size_bytes"],
                    "created_at": item["created_at"],
                    "url": f"/api/reports/media/{item['id']}",
                }
                for item in media
            ],
        }
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Report database is unavailable.") from None
