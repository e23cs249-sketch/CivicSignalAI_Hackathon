import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.auth import current_team_user, require_citizen_user, require_same_origin
from app.database import (
    attach_citizen_media,
    create_report_with_initial_event,
    get_duplicate_candidates,
    get_media_item,
    get_report_citizen_id,
    get_report_media,
    list_citizen_reports,
)
from app.models import Report, ReportEvent
from app.schemas import PreviewResponse, ReportCreateResponse, ReportInput
from app.services.analysis import analyze_report
from app.services.duplicates import find_duplicate_suggestions
from app.services.media import MAX_IMAGE_COUNT, resolve_stored_path, validate_and_store_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])
ANALYSIS_UNAVAILABLE = "Analysis unavailable; your report was saved without suggestions."


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@router.post("/preview", response_model=PreviewResponse)
def preview_report(
    payload: ReportInput,
    _: dict[str, str] = Depends(require_citizen_user),
) -> PreviewResponse:
    try:
        existing_reports = get_duplicate_candidates()
    except sqlite3.Error:
        logger.exception("Could not read reports for duplicate preview")
        raise HTTPException(status_code=500, detail="Database unavailable.") from None

    try:
        analysis = analyze_report(payload.description, payload.landmark)
        duplicates = find_duplicate_suggestions(
            payload.description,
            payload.category.value,
            existing_reports,
        )
    except Exception:
        logger.exception("Rule-based preview failed")
        raise HTTPException(
            status_code=503,
            detail="Analysis unavailable; you may still submit your report.",
        ) from None

    return PreviewResponse(
        source="rule_based",
        summary=analysis.summary,
        category_suggestion=analysis.category_suggestion,
        priority_hint=analysis.priority_hint,
        missing_fields=analysis.missing_fields,
        duplicate_suggestions=[
            {
                "id": item.id,
                "summary": item.summary,
                "match_reason": item.match_reason,
            }
            for item in duplicates
        ],
    )


@router.post("", status_code=201)
def create_report(
    payload: ReportInput,
    request: Request,
    citizen: dict[str, str] = Depends(require_citizen_user),
) -> dict[str, object]:
    require_same_origin(request)
    timestamp = utc_timestamp()
    report_id = str(uuid4())
    analysis_source = "rule_based"
    analysis_warning: str | None = None

    try:
        analysis = analyze_report(payload.description, payload.landmark)
        summary = analysis.summary
        priority_hint = analysis.priority_hint
    except Exception:
        logger.exception("Rule-based analysis failed during report creation")
        analysis_source = "unavailable"
        summary = None
        priority_hint = None
        analysis_warning = ANALYSIS_UNAVAILABLE

    category = payload.category.value
    legacy_category = category if category in {
        "overflowing_garbage", "broken_streetlight", "damaged_road", "water_leak", "unsafe_sidewalk"
    } else "damaged_road"
    report = Report(
        id=report_id,
        description=payload.description,
        category=legacy_category,
        landmark=payload.landmark,
        status="submitted",
        summary=summary,
        priority_hint=priority_hint,
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=None,
        resolution_note=None,
        demo_data_flag=False,
        analysis_source=analysis_source,
        title=payload.title,
        area=payload.area,
        latitude=payload.latitude,
        longitude=payload.longitude,
        reported_category=category,
    )
    initial_event = ReportEvent(
        id=str(uuid4()),
        report_id=report_id,
        event_type="created",
        actor_type="citizen",
        actor_name="Citizen",
        message="Report submitted",
        status_from=None,
        status_to="submitted",
        evidence_note=None,
        created_at=timestamp,
    )

    try:
        create_report_with_initial_event(report, initial_event, citizen_id=citizen["id"])
    except sqlite3.Error:
        logger.exception("Could not persist report and initial event")
        raise HTTPException(status_code=500, detail="Report could not be saved.") from None
    except Exception:
        logger.exception("Unexpected persistence failure")
        raise HTTPException(status_code=500, detail="Report could not be saved.") from None

    response_data: dict[str, object] = {
        "id": report.id,
        "title": report.title,
        "description": report.description,
        "category": category,
        "area": report.area,
        "landmark": report.landmark,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "status": report.status,
        "summary": report.summary,
        "priority_hint": report.priority_hint,
        "analysis_source": report.analysis_source,
        "demo_data_flag": report.demo_data_flag,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "resolved_at": report.resolved_at,
        "resolution_note": report.resolution_note,
        "timeline": [
            {
                "id": initial_event.id,
                "report_id": initial_event.report_id,
                "event_type": initial_event.event_type,
                "actor_type": initial_event.actor_type,
                "actor_name": initial_event.actor_name,
                "message": initial_event.message,
                "status_from": initial_event.status_from,
                "status_to": initial_event.status_to,
                "evidence_note": initial_event.evidence_note,
                "created_at": initial_event.created_at,
            }
        ],
    }
    if analysis_warning is not None:
        response_data["analysis_warning"] = analysis_warning
    response = ReportCreateResponse.model_validate(response_data)
    return response.model_dump(mode="json", exclude_unset=True)


def _public_media_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "id": item["id"],
        "event_id": item.get("event_id"),
        "uploader_role": item["uploader_role"],
        "media_type": item["media_type"],
        "content_type": item["content_type"],
        "size_bytes": item["size_bytes"],
        "created_at": item["created_at"],
        "url": f"/api/reports/media/{item['id']}",
    }


@router.get("/mine")
def my_reports(citizen: dict[str, str] = Depends(require_citizen_user)) -> dict[str, object]:
    try:
        reports = list_citizen_reports(citizen["id"])
        for report in reports:
            report["images"] = [
                _public_media_item(item) for item in get_report_media(str(report["id"]))
            ]
        return {"reports": reports}
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Report database is unavailable.") from None


@router.post("/{report_id}/images", status_code=201)
async def upload_original_images(
    report_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
    citizen: dict[str, str] = Depends(require_citizen_user),
) -> dict[str, object]:
    require_same_origin(request)
    if get_report_citizen_id(report_id) != citizen["id"]:
        raise HTTPException(status_code=404, detail="Report was not found.")
    if not files or len(files) > MAX_IMAGE_COUNT:
        raise HTTPException(status_code=400, detail=f"Choose between 1 and {MAX_IMAGE_COUNT} photos.")

    stored: list[dict[str, str]] = []
    try:
        for upload in files:
            stored.append(await validate_and_store_upload(upload))
        timestamp = utc_timestamp()
        items = [
            {
                "id": item["id"],
                "storage_path": item["path"],
                "content_type": item["content_type"],
                "size_bytes": item["size"],
            }
            for item in stored
        ]
        if not attach_citizen_media(
            report_id=report_id,
            citizen_id=citizen["id"],
            media_items=items,
            timestamp=timestamp,
        ):
            raise HTTPException(status_code=404, detail="Report was not found.")
        return {"images": [_public_media_item(item) for item in get_report_media(report_id)]}
    except HTTPException:
        for item in stored:
            Path(item["path"]).unlink(missing_ok=True)
        raise
    except Exception:
        for item in stored:
            Path(item["path"]).unlink(missing_ok=True)
        logger.exception("Could not save citizen report photos")
        raise HTTPException(status_code=500, detail="Photos could not be saved.") from None
    finally:
        for upload in files:
            await upload.close()


@router.get("/media/{media_id}")
def get_report_image(media_id: str, request: Request) -> FileResponse:
    team_user = current_team_user(request)
    citizen_user = None if team_user else require_citizen_user(request)
    try:
        item = get_media_item(media_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Image was not found.")
        if team_user is None and get_report_citizen_id(str(item["report_id"])) != citizen_user["id"]:
            raise HTTPException(status_code=404, detail="Image was not found.")
        path = resolve_stored_path(str(item["storage_path"]))
        return FileResponse(
            path,
            media_type=str(item["content_type"]),
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image was not found.") from None
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Report database is unavailable.") from None
