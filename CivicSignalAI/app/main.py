import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.auth import current_citizen_user, current_team_user, citizen_router, router as auth_router
from app.api.reports import router as reports_router
from app.api.team import router as team_router
from app.database import initialize_database

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="CivicSignal AI", lifespan=lifespan)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(citizen_router)
app.include_router(reports_router)
app.include_router(team_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exception: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exception.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in {"body", "query", "path"}]
        error_type = str(error.get("type", "invalid"))
        if error_type == "missing":
            code = "required"
        elif error_type == "string_too_long":
            code = "too_long"
        elif error_type == "string_too_short":
            code = "too_short"
        elif error_type == "json_invalid":
            code = "invalid_json"
            location = ["$"]
        else:
            code = "invalid"
        errors.append(
            {
                "field": ".".join(location) or "$",
                "code": code,
                "message": str(error.get("msg", "Invalid value")),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exception: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exception)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", include_in_schema=False)
def citizen_auth_page(request: Request) -> Response:
    if current_citizen_user(request) is not None:
        return RedirectResponse(url="/home", status_code=303)
    return FileResponse(STATIC_DIR / "auth.html")


@app.get("/home", include_in_schema=False)
def citizen_home_page(request: Request) -> Response:
    if current_citizen_user(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/report", include_in_schema=False)
@app.get("/report.html", include_in_schema=False)
def citizen_report_page(request: Request) -> Response:
    if current_citizen_user(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "report.html", headers={"Cache-Control": "no-store"})


@app.get("/static/index.html", include_in_schema=False)
def direct_citizen_page(request: Request) -> Response:
    if current_citizen_user(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/static/report.html", include_in_schema=False)
def direct_report_page(request: Request) -> Response:
    if current_citizen_user(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "report.html", headers={"Cache-Control": "no-store"})


@app.get("/team.html", include_in_schema=True)
@app.get("/team", include_in_schema=True)
def team_page(request: Request) -> Response:
    if current_team_user(request) is None:
        return RedirectResponse(url="/team-login?next=%2Fteam", status_code=303)
    return FileResponse(STATIC_DIR.parent / "team.html")


@app.get("/team-login", include_in_schema=False)
def team_login_page(request: Request) -> Response:
    if current_team_user(request) is not None:
        return RedirectResponse(url="/team", status_code=303)
    return FileResponse(STATIC_DIR.parent / "team-login.html")


@app.get("/team-signup", include_in_schema=False)
def team_signup_page() -> FileResponse:
    return FileResponse(STATIC_DIR.parent / "team-signup.html")


@app.get("/tracking.html", include_in_schema=True)
def tracking_page(request: Request) -> Response:
    if current_citizen_user(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR.parent / "tracking.html", headers={"Cache-Control": "no-store"})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
