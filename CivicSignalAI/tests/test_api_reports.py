import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import database
from app.api import reports as report_routes
from app.main import app


VALID_REPORT = {
    "description": "The streetlight is out on Cedar Street.",
    "category": "broken_streetlight",
    "landmark": "  Cedar Street near the library  ",
}


def row_counts(database_path):
    connection = database.connect_database(database_path)
    try:
        return (
            connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM report_events").fetchone()[0],
        )
    finally:
        connection.close()


class ApiReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "civicsignal-test.db"
        self.environment = patch.dict(
            os.environ,
            {
                "DATABASE_URL": "",
                "CIVICSIGNAL_DATABASE_PATH": str(self.database_path),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client_context = TestClient(app, raise_server_exceptions=False)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.citizen_email = "citizen@example.test"
        self.citizen_password = "valid-citizen-password"
        registration = self.client.post("/api/auth/citizen/register", json={
            "full_name": "Test Citizen",
            "email": self.citizen_email,
            "phone": "5551234567",
            "password": self.citizen_password,
            "confirm_password": self.citizen_password,
            "accepted_terms": True,
        })
        if registration.status_code != 200:
            raise AssertionError(registration.text)

    def test_health_endpoint_is_exact(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_citizen_page_and_static_assets_are_served(self):
        anonymous = TestClient(app, follow_redirects=False)
        page = anonymous.get("/")
        protected = anonymous.get("/home")
        direct_file = anonymous.get("/static/index.html")
        script = self.client.get("/static/js/app.js")
        stylesheet = self.client.get("/static/css/styles.css")
        self.assertEqual(page.status_code, 200)
        self.assertIn("citizen-login-form", page.text)
        self.assertEqual(protected.status_code, 303)
        self.assertEqual(direct_file.status_code, 303)
        self.assertEqual(self.client.get("/home").status_code, 200)
        home = self.client.get("/home")
        report_page = self.client.get("/report")
        self.assertIn("About", home.text)
        self.assertNotIn('id="report-form"', home.text)
        self.assertIn('id="report-form"', report_page.text)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)

    def test_team_login_page_serves_invitation_only_message(self):
        response = self.client.get("/team-login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation-only access", response.text)
        self.assertIn("Team dashboard", response.text)

    def test_invalid_report_fields_return_field_level_422(self):
        cases = [
            ({"category": "broken_streetlight"}, "description"),
            ({"description": "   ", "category": "broken_streetlight"}, "description"),
            ({"description": "Streetlight is out"}, "category"),
            ({"description": "Streetlight is out", "category": "invalid"}, "category"),
            ({"description": "x" * 2001, "category": "damaged_road"}, "description"),
            ({"description": "Streetlight is out", "category": "broken_streetlight", "landmark": "x" * 201}, "landmark"),
        ]
        for payload, field in cases:
            with self.subTest(field=field, payload=payload):
                response = self.client.post("/api/reports/preview", json=payload)
                self.assertEqual(response.status_code, 422)
                body = response.json()
                self.assertEqual(body["detail"], "Validation failed")
                self.assertTrue(any(error["field"] == field for error in body["errors"]))

    def test_invalid_json_returns_consistent_422(self):
        response = self.client.post("/api/reports/preview", content="{")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["errors"][0]["field"], "$")

    def test_extra_analysis_fields_are_rejected(self):
        payload = {**VALID_REPORT, "summary": "client supplied"}
        response = self.client.post("/api/reports", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertTrue(any(error["field"] == "summary" for error in response.json()["errors"]))

    def test_preview_normalizes_landmark_and_does_not_write(self):
        before = row_counts(self.database_path)
        response = self.client.post("/api/reports/preview", json=VALID_REPORT)
        after = row_counts(self.database_path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "rule_based")
        self.assertEqual(response.json()["summary"], "The streetlight is out on Cedar Street.")
        self.assertEqual(after, before)
        self.assertEqual(after, (0, 0))

    def test_blank_landmark_normalizes_to_null_for_preview_and_create(self):
        payload = {"description": "Streetlight out", "category": "broken_streetlight", "landmark": "  "}
        preview = self.client.post("/api/reports/preview", json=payload)
        created = self.client.post("/api/reports", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["missing_fields"], ["Add a nearby landmark if you can."])
        self.assertEqual(created.status_code, 201)
        self.assertIsNone(created.json()["landmark"])

    def test_duplicate_preview_is_advisory_and_create_succeeds(self):
        first = self.client.post("/api/reports", json=VALID_REPORT)
        self.assertEqual(first.status_code, 201)
        duplicate_input = {
            "description": "Streetlight out on Cedar Street",
            "category": "broken_streetlight",
            "landmark": "Cedar Street",
        }
        preview = self.client.post("/api/reports/preview", json=duplicate_input)
        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.json()["duplicate_suggestions"])
        second = self.client.post("/api/reports", json=duplicate_input)
        self.assertEqual(second.status_code, 201)

    def test_create_recomputes_analysis_and_saves_initial_event(self):
        response = self.client.post("/api/reports", json=VALID_REPORT)
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["summary"], "The streetlight is out on Cedar Street.")
        self.assertEqual(body["analysis_source"], "rule_based")
        self.assertFalse(body["demo_data_flag"])
        self.assertEqual(len(body["timeline"]), 1)
        event = body["timeline"][0]
        self.assertEqual(event["event_type"], "created")
        self.assertEqual(event["report_id"], body["id"])
        self.assertEqual(event["message"], "Report submitted")
        self.assertEqual(row_counts(self.database_path), (1, 1))

    def test_preview_analysis_failure_returns_503_without_writes(self):
        with patch.object(report_routes, "analyze_report", side_effect=RuntimeError("private internal failure")):
            response = self.client.post("/api/reports/preview", json=VALID_REPORT)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Analysis unavailable; you may still submit your report."})
        self.assertEqual(row_counts(self.database_path), (0, 0))
        self.assertNotIn("private internal failure", response.text)

    def test_create_analysis_failure_still_persists_report_and_event(self):
        with patch.object(report_routes, "analyze_report", side_effect=RuntimeError("private internal failure")):
            response = self.client.post("/api/reports", json=VALID_REPORT)
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsNone(body["summary"])
        self.assertIsNone(body["priority_hint"])
        self.assertEqual(body["analysis_source"], "unavailable")
        self.assertEqual(body["analysis_warning"], "Analysis unavailable; your report was saved without suggestions.")
        self.assertEqual(len(body["timeline"]), 1)

    def test_create_database_failure_rolls_back_and_hides_exception(self):
        connection = database.connect_database(self.database_path)
        try:
            connection.execute(
                """
                CREATE TRIGGER reject_event BEFORE INSERT ON report_events
                BEGIN SELECT RAISE(ABORT, 'sensitive database detail'); END;
                """
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.post("/api/reports", json=VALID_REPORT)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Report could not be saved."})
        self.assertNotIn("sensitive database detail", response.text)
        self.assertEqual(row_counts(self.database_path), (0, 0))

    def test_preview_database_read_failure_returns_generic_500(self):
        connection = database.connect_database(self.database_path)
        try:
            connection.execute("DROP TABLE reports")
            connection.commit()
        finally:
            connection.close()

        response = self.client.post("/api/reports/preview", json=VALID_REPORT)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Database unavailable."})
        self.assertNotIn("no such table", response.text)
