import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import database
from app.main import app
from app.services.team_auth import provision_team_user


class TeamWorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {
            "CIVICSIGNAL_DATABASE_PATH": str(Path(self.temp.name) / "test.db")
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client_context = TestClient(app, raise_server_exceptions=False)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.staff_email = "staff@city.gov"
        self.staff_password = " correct horse battery staple "
        provision_team_user(self.staff_email, self.staff_password)
        citizen_password = "valid-citizen-password"
        citizen = self.client.post("/api/auth/citizen/register", json={
            "full_name": "Workflow Citizen",
            "email": "workflow@example.test",
            "phone": "5551234567",
            "password": citizen_password,
            "confirm_password": citizen_password,
            "accepted_terms": True,
        })
        if citizen.status_code != 200:
            raise AssertionError(citizen.text)

    def login_team(self):
        response = self.client.post("/api/auth/team/login", json={
            "email": self.staff_email,
            "password": self.staff_password,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def create_report(self):
        response = self.client.post("/api/reports", json={
            "description": "Streetlight is broken near the library.",
            "category": "broken_streetlight",
            "landmark": "Near the library"
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def test_team_queue_updates_and_dashboard_require_authentication(self):
        report_id = self.create_report()

        listing = self.client.get("/api/reports")
        self.assertEqual(listing.status_code, 401)

        update = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "acknowledged"},
        )
        self.assertEqual(update.status_code, 401)
        self.assertEqual(
            self.client.get(f"/api/reports/{report_id}/tracking").json()["report"]["status"],
            "submitted",
        )

        dashboard = self.client.get("/team", follow_redirects=False)
        self.assertEqual(dashboard.status_code, 303)
        self.assertIn("/team-login", dashboard.headers["location"])

    def test_team_login_session_protects_dashboard_and_can_be_revoked(self):
        login = self.login_team()
        cookie_header = login.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie_header)
        self.assertIn("samesite=strict", cookie_header)
        self.assertIn("max-age=28800", cookie_header)
        self.assertTrue(login.json()["authenticated"])
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 200)
        self.assertEqual(self.client.get("/team").status_code, 200)

        logout = self.client.post("/api/auth/team/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 401)
        self.assertEqual(self.client.get("/api/reports").status_code, 401)

    def test_invalid_team_login_is_generic_and_rate_limited(self):
        for _ in range(5):
            response = self.client.post("/api/auth/team/login", json={
                "email": self.staff_email,
                "password": "incorrect password",
            })
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Work email or password is incorrect.")

        limited = self.client.post("/api/auth/team/login", json={
            "email": self.staff_email,
            "password": self.staff_password,
        })
        self.assertEqual(limited.status_code, 429)

    def test_inactive_staff_account_cannot_create_a_session(self):
        connection = database.connect_database()
        try:
            connection.execute(
                "UPDATE team_users SET is_active = 0 WHERE email = ?",
                (self.staff_email,),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.post("/api/auth/team/login", json={
            "email": self.staff_email,
            "password": self.staff_password,
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Work email or password is incorrect.")
        self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 401)
        self.assertEqual(self.client.get("/team", follow_redirects=False).status_code, 303)

    def test_cross_origin_status_update_is_rejected(self):
        self.login_team()
        report_id = self.create_report()
        response = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "acknowledged"},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 403)
        tracking = self.client.get(f"/api/reports/{report_id}/tracking").json()
        self.assertEqual(tracking["report"]["status"], "submitted")

    def test_list_and_tracking_use_shared_persisted_report(self):
        self.login_team()
        report_id = self.create_report()
        listed = self.client.get("/api/reports")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["reports"][0]["id"], report_id)

        tracking = self.client.get(f"/api/reports/{report_id}/tracking")
        self.assertEqual(tracking.status_code, 200)
        self.assertEqual(tracking.json()["report"]["status"], "submitted")
        self.assertEqual(tracking.json()["timeline"][0]["event_type"], "created")

    def test_status_transitions_and_resolution_note(self):
        self.login_team()
        report_id = self.create_report()
        for status in ("acknowledged", "in_progress"):
            response = self.client.patch(
                f"/api/team/reports/{report_id}/status",
                json={"status": status, "message": f"Moved to {status}"},
            )
            self.assertEqual(response.status_code, 200, response.text)

        missing_note = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "resolved"},
        )
        self.assertEqual(missing_note.status_code, 409)

        resolved = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "resolved", "message": "Repaired and verified."},
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)
        tracking = self.client.get(f"/api/reports/{report_id}/tracking").json()
        self.assertEqual(tracking["report"]["status"], "resolved")
        self.assertEqual(tracking["report"]["resolution_note"], "Repaired and verified.")
        self.assertEqual(tracking["timeline"][-1]["event_type"], "resolved")
        self.assertEqual(tracking["timeline"][-1]["message"], "Repaired and verified.")

    def test_invalid_transition_does_not_change_report(self):
        self.login_team()
        report_id = self.create_report()
        response = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "resolved", "message": "Done"},
        )
        self.assertEqual(response.status_code, 409)
        tracking = self.client.get(f"/api/reports/{report_id}/tracking").json()
        self.assertEqual(tracking["report"]["status"], "submitted")
        self.assertEqual(len(tracking["timeline"]), 1)


class TeamAccountProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database_path = str(Path(self.temp.name) / "accounts.db")

    def test_app_start_does_not_create_a_team_account(self):
        with patch.dict(os.environ, {
            "CIVICSIGNAL_DATABASE_PATH": self.database_path,
        }):
            with TestClient(app):
                self.assertIsNone(database.get_team_user("staff@city.gov"))
