import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import database
from app.main import app


class TeamWorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {
            "DATABASE_URL": "",
            "CIVICSIGNAL_DATABASE_PATH": str(Path(self.temp.name) / "test.db"),
            "ADMIN_USERNAME": "staff-admin",
            "ADMIN_PASSWORD": " correct horse battery staple ",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret-with-32-bytes",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client_context = TestClient(app, raise_server_exceptions=False)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.staff_username = "staff-admin"
        self.staff_password = " correct horse battery staple "
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
            "username": self.staff_username,
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
        self.assertEqual(login.json()["username"], self.staff_username)
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 200)
        self.assertEqual(self.client.get("/team").status_code, 200)

        logout = self.client.post("/api/auth/team/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 401)
        self.assertEqual(self.client.get("/api/reports").status_code, 401)

    def test_admin_cookie_is_secure_on_vercel(self):
        with patch.dict(os.environ, {
            "VERCEL": "1",
            "CIVICSIGNAL_COOKIE_SECURE": "false",
        }):
            login = self.client.post("/api/auth/team/login", json={
                "username": self.staff_username,
                "password": self.staff_password,
            })

        self.assertEqual(login.status_code, 200, login.text)
        self.assertIn("secure", login.headers["set-cookie"].lower())

    def test_https_cookie_stays_secure_when_setting_is_false(self):
        with patch.dict(os.environ, {"CIVICSIGNAL_COOKIE_SECURE": "false"}):
            with TestClient(
                app,
                base_url="https://testserver",
                raise_server_exceptions=False,
            ) as https_client:
                login = https_client.post(
                    "/api/auth/team/login",
                    json={
                        "username": self.staff_username,
                        "password": self.staff_password,
                    },
                )

        self.assertEqual(login.status_code, 200, login.text)
        self.assertIn("secure", login.headers["set-cookie"].lower())

    def test_admin_login_and_session_do_not_access_the_database(self):
        with patch.object(database, "connect_database", side_effect=AssertionError("database used")):
            login = self.login_team()
            self.assertEqual(login.status_code, 200)
            self.assertEqual(self.client.get("/api/auth/team/me").status_code, 200)
            self.assertEqual(self.client.get("/team").status_code, 200)

    def test_incorrect_admin_credentials_are_rejected(self):
        for credentials in (
            {"username": self.staff_username, "password": "incorrect password"},
            {"username": "unknown-admin", "password": self.staff_password},
        ):
            with self.subTest(credentials="invalid"):
                response = self.client.post("/api/auth/team/login", json=credentials)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["detail"], "Username or password is incorrect.")
                self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 401)
        dashboard = self.client.get("/team", follow_redirects=False)
        self.assertEqual(dashboard.status_code, 303)
        self.assertIn("/team-login", dashboard.headers["location"])

    def test_tampered_admin_session_is_rejected(self):
        self.login_team()
        token = self.client.cookies.get("civicsignal_team_session")
        self.client.cookies.set("civicsignal_team_session", token + "tampered")

        self.assertEqual(self.client.get("/api/auth/team/me").status_code, 401)
        self.assertEqual(self.client.get("/team", follow_redirects=False).status_code, 303)

    def test_missing_admin_configuration_fails_closed(self):
        with patch.dict(os.environ, {
            "ADMIN_USERNAME": "",
            "ADMIN_PASSWORD": "",
            "ADMIN_SESSION_SECRET": "",
        }):
            response = self.client.post("/api/auth/team/login", json={
                "username": self.staff_username,
                "password": self.staff_password,
            })

        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"])
        self.assertNotIn("set-cookie", response.headers)

    def test_cross_origin_admin_login_is_rejected(self):
        response = self.client.post(
            "/api/auth/team/login",
            json={"username": self.staff_username, "password": self.staff_password},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("set-cookie", response.headers)

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


class TeamAuthenticationSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database_path = str(Path(self.temp.name) / "accounts.db")

    def test_app_does_not_create_admin_auth_tables(self):
        with patch.dict(os.environ, {
            "DATABASE_URL": "",
            "CIVICSIGNAL_DATABASE_PATH": self.database_path,
        }):
            with TestClient(app):
                connection = database.connect_database()
                try:
                    tables = {
                        row["name"] for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                finally:
                    connection.close()
                self.assertNotIn("team_users", tables)
                self.assertNotIn("team_sessions", tables)
                self.assertIn("team_login_attempts", tables)
