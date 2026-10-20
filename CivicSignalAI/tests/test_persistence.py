import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.database import connect_database, create_report_with_initial_event, initialize_database
from app.models import Report, ReportEvent


def make_report_and_event():
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report_id = str(uuid4())
    report = Report(
        id=report_id,
        description="Streetlight is out",
        category="broken_streetlight",
        landmark=None,
        status="submitted",
        summary="Streetlight is out",
        priority_hint=None,
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=None,
        resolution_note=None,
        demo_data_flag=False,
        analysis_source="rule_based",
    )
    event = ReportEvent(
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
    return report, event


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.path = Path(self.temporary_directory.name) / "data" / "test.db"

    def test_initialize_database_creates_citizen_and_report_tables(self):
        initialize_database(self.path)
        connection = connect_database(self.path)
        try:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertEqual(
                tables,
                {
                    "reports",
                    "report_events",
                    "citizen_users",
                    "citizen_sessions",
                    "report_media",
                    "team_login_attempts",
                },
            )
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            connection.close()

    def test_report_and_initial_event_persist_after_reopen(self):
        initialize_database(self.path)
        report, event = make_report_and_event()
        create_report_with_initial_event(report, event, self.path)

        connection = connect_database(self.path)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM report_events").fetchone()[0], 1)
            stored_event = connection.execute("SELECT * FROM report_events").fetchone()
            self.assertEqual(stored_event["report_id"], report.id)
        finally:
            connection.close()

    def test_initialize_database_adds_citizen_owner_without_replacing_existing_reports(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "CREATE TABLE reports (id TEXT PRIMARY KEY NOT NULL, description TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO reports (id, description) VALUES (?, ?)",
                ("legacy-report", "Existing issue"),
            )
            connection.commit()
        finally:
            connection.close()

        initialize_database(self.path)
        connection = connect_database(self.path)
        try:
            row = connection.execute(
                "SELECT id, description, citizen_id FROM reports WHERE id = ?",
                ("legacy-report",),
            ).fetchone()
            self.assertEqual(row["id"], "legacy-report")
            self.assertEqual(row["description"], "Existing issue")
            self.assertIsNone(row["citizen_id"])
        finally:
            connection.close()

    def test_initial_event_failure_rolls_back_report_and_event(self):
        initialize_database(self.path)
        report, event = make_report_and_event()
        connection = connect_database(self.path)
        try:
            connection.execute(
                """
                CREATE TRIGGER reject_event BEFORE INSERT ON report_events
                BEGIN SELECT RAISE(ABORT, 'forced event failure'); END;
                """
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            create_report_with_initial_event(report, event, self.path)

        connection = connect_database(self.path)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM report_events").fetchone()[0], 0)
        finally:
            connection.close()
