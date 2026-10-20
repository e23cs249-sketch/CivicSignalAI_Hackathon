from pathlib import Path
import os
import sqlite3
from uuid import uuid4

from app.config import get_database_path, get_database_url
from app.models import DuplicateCandidate, Report, ReportEvent

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

DATABASE_ERRORS = (sqlite3.Error,) + ((psycopg.Error,) if psycopg is not None else ())
INTEGRITY_ERRORS = (sqlite3.IntegrityError,) + (
    (psycopg.IntegrityError,) if psycopg is not None else ()
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY NOT NULL,
    description TEXT NOT NULL CHECK(length(trim(description)) BETWEEN 1 AND 2000),
    category TEXT NOT NULL CHECK(category IN (
        'overflowing_garbage',
        'broken_streetlight',
        'damaged_road',
        'water_leak',
        'unsafe_sidewalk'
    )),
    landmark TEXT CHECK(landmark IS NULL OR (length(trim(landmark)) BETWEEN 1 AND 200)),
    status TEXT NOT NULL DEFAULT 'submitted'
        CHECK(status IN ('submitted', 'acknowledged', 'in_progress', 'resolved')),
    summary TEXT,
    priority_hint TEXT CHECK(priority_hint IS NULL OR priority_hint IN ('low', 'medium', 'high')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution_note TEXT,
    demo_data_flag INTEGER NOT NULL DEFAULT 0 CHECK(demo_data_flag IN (0, 1)),
    analysis_source TEXT NOT NULL CHECK(analysis_source IN ('rule_based', 'unavailable')),
    CHECK(status != 'resolved' OR (resolution_note IS NOT NULL AND length(trim(resolution_note)) > 0))
);

CREATE TABLE IF NOT EXISTS report_events (
    id TEXT PRIMARY KEY NOT NULL,
    report_id TEXT NOT NULL REFERENCES reports(id),
    event_type TEXT NOT NULL CHECK(event_type IN (
        'created', 'status_changed', 'progress_note', 'evidence_added', 'resolved'
    )),
    actor_type TEXT NOT NULL CHECK(actor_type IN ('citizen', 'team')),
    actor_name TEXT NOT NULL,
    message TEXT NOT NULL,
    status_from TEXT CHECK(status_from IS NULL OR status_from IN (
        'submitted', 'acknowledged', 'in_progress', 'resolved'
    )),
    status_to TEXT CHECK(status_to IS NULL OR status_to IN (
        'submitted', 'acknowledged', 'in_progress', 'resolved'
    )),
    evidence_note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_media (
    id TEXT PRIMARY KEY NOT NULL,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    event_id TEXT REFERENCES report_events(id) ON DELETE SET NULL,
    uploader_id TEXT NOT NULL,
    uploader_role TEXT NOT NULL CHECK(uploader_role IN ('citizen', 'team')),
    media_type TEXT NOT NULL CHECK(media_type IN ('original', 'progress')),
    storage_path TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK(content_type IN ('image/jpeg', 'image/png', 'image/webp')),
    size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS report_media_report_created
    ON report_media (report_id, created_at, id);

CREATE TABLE IF NOT EXISTS citizen_users (
    id TEXT PRIMARY KEY NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE COLLATE NOCASE NOT NULL,
    phone TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    accepted_terms INTEGER NOT NULL DEFAULT 0 CHECK(accepted_terms IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS citizen_sessions (
    token_hash TEXT PRIMARY KEY NOT NULL,
    user_id TEXT NOT NULL REFERENCES citizen_users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS team_login_attempts (
    id TEXT PRIMARY KEY NOT NULL,
    remote_addr TEXT NOT NULL,
    attempted_at INTEGER NOT NULL
);

"""


class PostgresConnection:
    def __init__(self, connection) -> None:
        self._connection = connection

    def execute(self, query: str, parameters=()):
        if query.strip().upper() == "BEGIN IMMEDIATE":
            query = "BEGIN"
        return self._connection.execute(query.replace("?", "%s"), parameters)

    def executemany(self, query: str, parameters):
        return self._connection.executemany(query.replace("?", "%s"), parameters)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def connect_database(path: str | Path | None = None) -> sqlite3.Connection | PostgresConnection:
    database_url = get_database_url() if path is None else None
    if database_url:
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL.")
        if psycopg is None or dict_row is None:
            raise RuntimeError("Install the psycopg[binary] dependency to use DATABASE_URL.")
        connection = psycopg.connect(
            database_url,
            connect_timeout=10,
            sslmode="require",
            row_factory=dict_row,
        )
        return PostgresConnection(connection)
    if path is None and os.getenv("VERCEL") == "1":
        raise RuntimeError("DATABASE_URL must be configured on Vercel; SQLite is local-only.")

    database_path = Path(path) if path is not None else get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: str | Path | None = None) -> None:
    connection = connect_database(path)
    try:
        is_postgres = isinstance(connection, PostgresConnection)
        if is_postgres:
            for statement in SCHEMA.replace(" COLLATE NOCASE", "").split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.execute(
                """ALTER TABLE report_events ADD COLUMN IF NOT EXISTS
                   event_sequence BIGINT GENERATED BY DEFAULT AS IDENTITY"""
            )
            report_columns = {
                row["column_name"]
                for row in connection.execute(
                    """SELECT column_name FROM information_schema.columns
                       WHERE table_schema = current_schema() AND table_name = 'reports'"""
                ).fetchall()
            }
        else:
            connection.executescript(SCHEMA)
            report_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(reports)").fetchall()
            }
        if "citizen_id" not in report_columns:
            if is_postgres:
                connection.execute(
                    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS citizen_id TEXT "
                    "REFERENCES citizen_users(id) ON DELETE SET NULL"
                )
            else:
                connection.execute(
                    "ALTER TABLE reports ADD COLUMN citizen_id TEXT "
                    "REFERENCES citizen_users(id) ON DELETE SET NULL"
                )
        for name, definition in (
            ("title", "TEXT"),
            ("area", "TEXT"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
            ("reported_category", "TEXT"),
            ("workflow_status", "TEXT"),
        ):
            if name not in report_columns:
                if is_postgres:
                    connection.execute(
                        f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS {name} {definition}"
                    )
                else:
                    connection.execute(f"ALTER TABLE reports ADD COLUMN {name} {definition}")
        connection.commit()
    finally:
        connection.close()


def create_citizen_user(user_id: str, full_name: str, email: str, phone: str, password_hash: str, accepted_terms: bool, created_at: str) -> None:
    connection = connect_database()
    try:
        connection.execute(
            "INSERT INTO citizen_users (id, full_name, email, phone, password_hash, accepted_terms, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (user_id, full_name, email, phone, password_hash, int(bool(accepted_terms)), created_at),
        )
        connection.commit()
    finally:
        connection.close()


def get_citizen_user_by_email(email: str) -> dict[str, object] | None:
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT id, full_name, email, phone, password_hash, accepted_terms, is_active FROM citizen_users WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def create_citizen_session(token_hash: str, user_id: str, email: str, expires_at: int) -> None:
    connection = connect_database()
    try:
        connection.execute(
            "INSERT INTO citizen_sessions (token_hash, user_id, email, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, email, expires_at),
        )
        connection.commit()
    finally:
        connection.close()


def get_citizen_session(token_hash: str, now: int) -> dict[str, object] | None:
    connection = connect_database()
    try:
        row = connection.execute(
            """SELECT sessions.user_id, sessions.email
               FROM citizen_sessions AS sessions
               JOIN citizen_users AS users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                 AND users.is_active = 1""",
            (token_hash, now),
        ).fetchone()
        if row is None:
            connection.execute("DELETE FROM citizen_sessions WHERE expires_at <= ?", (now,))
            connection.commit()
            return None
        return dict(row)
    finally:
        connection.close()


def delete_citizen_session(token_hash: str) -> None:
    connection = connect_database()
    try:
        connection.execute("DELETE FROM citizen_sessions WHERE token_hash = ?", (token_hash,))
        connection.commit()
    finally:
        connection.close()


def count_recent_team_login_attempts(remote_addr: str, since: int) -> int:
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS attempts FROM team_login_attempts WHERE remote_addr = ? AND attempted_at >= ?",
            (remote_addr, since),
        ).fetchone()
        return int(row["attempts"])
    finally:
        connection.close()


def record_team_login_attempt(remote_addr: str, attempted_at: int) -> None:
    connection = connect_database()
    try:
        connection.execute(
            "DELETE FROM team_login_attempts WHERE attempted_at < ?",
            (attempted_at - 3600,),
        )
        connection.execute(
            "INSERT INTO team_login_attempts (id, remote_addr, attempted_at) VALUES (?, ?, ?)",
            (str(uuid4()), remote_addr, attempted_at),
        )
        connection.commit()
    finally:
        connection.close()


def clear_team_login_attempts(remote_addr: str) -> None:
    connection = connect_database()
    try:
        connection.execute("DELETE FROM team_login_attempts WHERE remote_addr = ?", (remote_addr,))
        connection.commit()
    finally:
        connection.close()


def get_duplicate_candidates() -> list[DuplicateCandidate]:
    connection = connect_database()
    try:
        rows = connection.execute(
            "SELECT id, description, category, summary FROM reports ORDER BY id"
        ).fetchall()
        return [
            DuplicateCandidate(
                id=row["id"],
                description=row["description"],
                category=row["category"],
                summary=row["summary"],
            )
            for row in rows
        ]
    finally:
        connection.close()


def create_report_with_initial_event(
    report: Report,
    event: ReportEvent,
    path: str | Path | None = None,
    citizen_id: str | None = None,
    media_items: list[dict[str, object]] | None = None,
) -> None:
    connection = connect_database(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO reports (
                id, description, category, landmark, status, summary, priority_hint,
                created_at, updated_at, resolved_at, resolution_note,
                demo_data_flag, analysis_source, citizen_id, title, area,
                latitude, longitude, reported_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.description,
                report.category,
                report.landmark,
                report.status,
                report.summary,
                report.priority_hint,
                report.created_at,
                report.updated_at,
                report.resolved_at,
                report.resolution_note,
                int(report.demo_data_flag),
                report.analysis_source,
                citizen_id,
                report.title,
                report.area,
                report.latitude,
                report.longitude,
                report.reported_category,
            ),
        )
        connection.execute(
            """
            INSERT INTO report_events (
                id, report_id, event_type, actor_type, actor_name, message,
                status_from, status_to, evidence_note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.report_id,
                event.event_type,
                event.actor_type,
                event.actor_name,
                event.message,
                event.status_from,
                event.status_to,
                event.evidence_note,
                event.created_at,
            ),
        )
        for item in media_items or []:
            connection.execute(
                """INSERT INTO report_media (
                       id, report_id, event_id, uploader_id, uploader_role,
                       media_type, storage_path, content_type, size_bytes, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(item["id"]), report.id, event.id,
                    str(item["uploader_id"]), str(item["uploader_role"]),
                    str(item["media_type"]), str(item["storage_path"]),
                    str(item["content_type"]), int(item["size_bytes"]),
                    str(item["created_at"]),
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# Team workflow persistence helpers. Keep report IDs as the UUID strings used by
# the existing reports table; status and timeline writes share one transaction.
def list_reports() -> list[dict[str, object]]:
    connection = connect_database()
    try:
        rows = connection.execute(
            """SELECT id, COALESCE(title, substr(description, 1, 100)) AS title,
                      COALESCE(reported_category, category) AS category,
                      description, landmark, area, latitude, longitude,
                      COALESCE(workflow_status, status) AS status, summary,
                      priority_hint, created_at, updated_at, resolved_at,
                      resolution_note, demo_data_flag, analysis_source
               FROM reports ORDER BY created_at DESC, id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_report(report_id: str) -> dict[str, object] | None:
    connection = connect_database()
    try:
        row = connection.execute(
            """SELECT id, COALESCE(title, substr(description, 1, 100)) AS title,
                      COALESCE(reported_category, category) AS category,
                      description, landmark, area, latitude, longitude,
                      COALESCE(workflow_status, status) AS status, summary,
                      priority_hint, created_at, updated_at, resolved_at,
                      resolution_note, demo_data_flag, analysis_source
               FROM reports WHERE id = ?""",
            (report_id,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def get_report_citizen_id(report_id: str) -> str | None:
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT citizen_id FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
        return str(row["citizen_id"]) if row and row["citizen_id"] is not None else None
    finally:
        connection.close()


def get_report_events(report_id: str) -> list[dict[str, object]]:
    connection = connect_database()
    try:
        event_order = (
            "created_at ASC, event_sequence ASC"
            if isinstance(connection, PostgresConnection)
            else "created_at ASC, rowid ASC"
        )
        rows = connection.execute(
            f"""SELECT id, report_id, event_type, actor_type, actor_name, message,
                      status_from, status_to, evidence_note, created_at
               FROM report_events WHERE report_id = ?
               ORDER BY {event_order}""",
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_report_media(report_id: str) -> list[dict[str, object]]:
    connection = connect_database()
    try:
        rows = connection.execute(
            """SELECT id, report_id, event_id, uploader_id, uploader_role,
                      media_type, storage_path, content_type, size_bytes, created_at
               FROM report_media WHERE report_id = ? ORDER BY created_at, id""",
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_media_item(media_id: str) -> dict[str, object] | None:
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT * FROM report_media WHERE id = ?", (media_id,)
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def list_citizen_reports(citizen_id: str) -> list[dict[str, object]]:
    connection = connect_database()
    try:
        event_order = (
            "event.created_at DESC, event.event_sequence DESC"
            if isinstance(connection, PostgresConnection)
            else "event.created_at DESC, event.rowid DESC"
        )
        rows = connection.execute(
            f"""SELECT id, COALESCE(title, substr(description, 1, 100)) AS title,
                      COALESCE(reported_category, category) AS category,
                      description, landmark, area, latitude, longitude,
                      COALESCE(workflow_status, status) AS status, created_at,
                     updated_at, resolution_note,
                     (SELECT message FROM report_events AS event
                      WHERE event.report_id = reports.id
                     ORDER BY {event_order} LIMIT 1) AS latest_update
                 FROM reports WHERE citizen_id = ? ORDER BY created_at DESC, id""",
            (citizen_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def add_team_update(
    *, report_id: str, status: str | None, message: str, actor: str,
    timestamp: str, media_items: list[dict[str, object]],
) -> tuple[str, str | None]:
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row_query = "SELECT status, workflow_status FROM reports WHERE id = ?"
        if isinstance(connection, PostgresConnection):
            row_query += " FOR UPDATE"
        row = connection.execute(row_query, (report_id,)).fetchone()
        if row is None:
            connection.rollback()
            return "missing", None
        previous = str(row["workflow_status"] or row["status"])
        next_status = status or previous
        if status and status != previous:
            from app.services.workflow import allowed_next_statuses
            if status not in allowed_next_statuses(previous):
                connection.rollback()
                return "invalid", previous
        if status == "resolved" and status != previous and not message.strip():
            connection.rollback()
            return "note_required", previous
        if status == "rejected" and status != previous and not message.strip():
            connection.rollback()
            return "reason_required", previous

        if status and status != previous:
            connection.execute(
                """UPDATE reports SET
                       status = CASE WHEN ? = 'rejected' THEN status ELSE ? END,
                       workflow_status = CASE WHEN ? = 'rejected' THEN 'rejected' ELSE NULL END,
                       updated_at = ?,
                       resolved_at = CASE WHEN ? = 'resolved' THEN ? ELSE NULL END,
                       resolution_note = CASE WHEN ? IN ('resolved', 'rejected') THEN ? ELSE resolution_note END
                   WHERE id = ?""",
                (status, status, status, timestamp, status, timestamp, status, message.strip(), report_id),
            )
        else:
            connection.execute("UPDATE reports SET updated_at = ? WHERE id = ?", (timestamp, report_id))

        event_id = str(uuid4())
        event_type = "status_changed" if status and status != previous else "progress_note"
        connection.execute(
            """INSERT INTO report_events (
                   id, report_id, event_type, actor_type, actor_name, message,
                   status_from, status_to, evidence_note, created_at
               ) VALUES (?, ?, ?, 'team', ?, ?, ?, ?, ?, ?)""",
            (
                event_id, report_id, event_type, actor,
                (f"Report rejected: {message.strip()}" if status == "rejected" and status != previous else message.strip()) or "Progress evidence added",
                previous if status and status != previous else None,
                status if status and status != previous and status != "rejected" else None,
                message.strip() or None, timestamp,
            ),
        )
        for item in media_items:
            connection.execute(
                """INSERT INTO report_media (
                       id, report_id, event_id, uploader_id, uploader_role,
                       media_type, storage_path, content_type, size_bytes, created_at
                   ) VALUES (?, ?, ?, ?, 'team', 'progress', ?, ?, ?, ?)""",
                (
                    str(item["id"]), report_id, event_id, actor,
                    str(item["storage_path"]), str(item["content_type"]),
                    int(item["size_bytes"]), timestamp,
                ),
            )
        connection.commit()
        return "saved", event_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def attach_citizen_media(
    *, report_id: str, citizen_id: str, media_items: list[dict[str, object]], timestamp: str,
) -> bool:
    if not media_items:
        return True
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        owner = connection.execute(
            "SELECT 1 FROM reports WHERE id = ? AND citizen_id = ?",
            (report_id, citizen_id),
        ).fetchone()
        if owner is None:
            connection.rollback()
            return False
        event_id = str(uuid4())
        connection.execute(
            """INSERT INTO report_events (
                   id, report_id, event_type, actor_type, actor_name, message,
                   status_from, status_to, evidence_note, created_at
               ) VALUES (?, ?, 'evidence_added', 'citizen', 'Citizen', ?, NULL, NULL, NULL, ?)""",
            (event_id, report_id, "Original report photos added", timestamp),
        )
        for item in media_items:
            connection.execute(
                """INSERT INTO report_media (
                       id, report_id, event_id, uploader_id, uploader_role,
                       media_type, storage_path, content_type, size_bytes, created_at
                   ) VALUES (?, ?, ?, ?, 'citizen', 'original', ?, ?, ?, ?)""",
                (
                    str(item["id"]), report_id, event_id, citizen_id,
                    str(item["storage_path"]), str(item["content_type"]),
                    int(item["size_bytes"]), timestamp,
                ),
            )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def insert_report_media(items: list[dict[str, object]]) -> None:
    if not items:
        return
    connection = connect_database()
    try:
        connection.executemany(
            """INSERT INTO report_media (
                   id, report_id, event_id, uploader_id, uploader_role,
                   media_type, storage_path, content_type, size_bytes, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    str(item["id"]), str(item["report_id"]), item.get("event_id"),
                    str(item["uploader_id"]), str(item["uploader_role"]),
                    str(item["media_type"]), str(item["storage_path"]),
                    str(item["content_type"]), int(item["size_bytes"]),
                    str(item["created_at"]),
                )
                for item in items
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def transition_status_and_add_event(
    *,
    report_id: str,
    expected_previous_status: str,
    new_status: str,
    actor: str,
    message: str,
    timestamp: str,
) -> bool:
    """Compare-and-set a status and append its timeline event atomically."""
    from uuid import uuid4

    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """UPDATE reports
               SET status = CASE WHEN ? = 'rejected' THEN status ELSE ? END,
                   workflow_status = CASE WHEN ? = 'rejected' THEN 'rejected' ELSE NULL END,
                   updated_at = ?, resolved_at = ?,
                   resolution_note = CASE WHEN ? IN ('resolved', 'rejected') THEN ? ELSE resolution_note END
               WHERE id = ? AND status = ?""",
            (
                new_status,
                new_status,
                new_status,
                timestamp,
                timestamp if new_status == "resolved" else None,
                new_status,
                message.strip() if new_status in {"resolved", "rejected"} else None,
                report_id,
                expected_previous_status,
            ),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            return False
        event_type = "resolved" if new_status == "resolved" else "status_changed"
        connection.execute(
            """INSERT INTO report_events (
                   id, report_id, event_type, actor_type, actor_name, message,
                   status_from, status_to, evidence_note, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid4()), report_id, event_type, "team", actor,
                message or f"Status changed to {new_status.replace('_', ' ')}",
                expected_previous_status, None if new_status == "rejected" else new_status,
                message if new_status in {"resolved", "rejected"} else None, timestamp,
            ),
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
