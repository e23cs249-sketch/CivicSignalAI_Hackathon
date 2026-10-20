import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class OAuthResponse:
    def __init__(self, payload):
        import json

        self.content = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, size=-1):
        return self.content if size < 0 else self.content[:size]


class CitizenAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {
            "DATABASE_URL": "",
            "CIVICSIGNAL_DATABASE_PATH": str(Path(self.temp.name) / "civicsignal.db"),
            "ADMIN_USERNAME": "test-admin",
            "ADMIN_PASSWORD": "a-valid-admin-password",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret-with-32-bytes",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client_context = TestClient(app, raise_server_exceptions=False)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.email = "citizen@example.test"
        self.password = "valid-citizen-password"

    def signup(self, email=None):
        return self.client.post("/api/auth/citizen/register", json={
            "full_name": "Test Citizen",
            "email": email or self.email,
            "phone": "5551234567",
            "password": self.password,
            "confirm_password": self.password,
            "accepted_terms": True,
        })

    def create_report(self):
        return self.client.post("/api/reports", json={
            "description": "The streetlight is out near the library.",
            "category": "broken_streetlight",
            "landmark": "Near the library",
        })

    def test_unauthenticated_visitors_are_gated_from_citizen_pages_and_apis(self):
        anonymous = TestClient(app, follow_redirects=False)
        root = anonymous.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertIn("citizen-login-form", root.text)
        for path in ("/home", "/report", "/report.html", "/tracking.html", "/static/index.html", "/static/report.html"):
            with self.subTest(path=path):
                self.assertEqual(anonymous.get(path).status_code, 303)

        self.assertEqual(anonymous.post("/api/reports/preview", json={
            "description": "Streetlight is out",
            "category": "broken_streetlight",
        }).status_code, 401)
        self.assertEqual(anonymous.post("/api/reports", json={
            "description": "Streetlight is out",
            "category": "broken_streetlight",
        }).status_code, 401)
        self.assertEqual(anonymous.get("/api/reports/not-a-report/tracking").status_code, 401)
        self.assertEqual(anonymous.get("/api/reports").status_code, 401)
        self.assertEqual(anonymous.get("/team", follow_redirects=False).status_code, 303)

    def test_registration_login_logout_and_session_persistence(self):
        registration = self.signup()
        self.assertEqual(registration.status_code, 200, registration.text)
        cookie = registration.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertEqual(self.client.get("/api/auth/citizen/me").status_code, 200)
        self.assertEqual(self.client.get("/home").status_code, 200)
        self.assertEqual(self.client.get("/report").status_code, 200)
        self.assertEqual(self.client.get("/report.html").status_code, 200)
        self.assertEqual(self.client.get("/tracking.html").status_code, 200)
        self.assertEqual(self.client.get("/team", follow_redirects=False).status_code, 303)

        duplicate = self.signup()
        self.assertEqual(duplicate.status_code, 409)
        logout = self.client.post("/api/auth/citizen/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/citizen/me").status_code, 401)
        self.assertEqual(self.client.get("/home", follow_redirects=False).status_code, 303)

        invalid_login = self.client.post("/api/auth/citizen/login", json={
            "email": self.email,
            "password": "incorrect-password",
        })
        self.assertEqual(invalid_login.status_code, 401)
        login = self.client.post("/api/auth/citizen/login", json={
            "email": self.email,
            "password": self.password,
        })
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(self.client.get("/home").status_code, 200)

    def test_registration_checks_terms_password_match_and_profile_fields(self):
        payload = {
            "full_name": "Test Citizen",
            "email": self.email,
            "phone": "5551234567",
            "password": self.password,
            "confirm_password": "another-valid-password",
            "accepted_terms": False,
        }
        terms = self.client.post("/api/auth/citizen/register", json=payload)
        self.assertEqual(terms.status_code, 400)
        payload["accepted_terms"] = True
        mismatch = self.client.post("/api/auth/citizen/register", json=payload)
        self.assertEqual(mismatch.status_code, 400)
        payload["confirm_password"] = self.password
        payload["full_name"] = "  "
        blank_name = self.client.post("/api/auth/citizen/register", json=payload)
        self.assertEqual(blank_name.status_code, 422)

    def test_oauth_links_verified_google_and_linkedin_accounts_server_side(self):
        self.assertEqual(self.signup().status_code, 200)
        state_secret = "test-oauth-state-secret-with-at-least-32-bytes"

        for provider, prefix, subject in (
            ("google", "GOOGLE", "google-subject"),
            ("linkedin", "LINKEDIN", "linkedin-subject"),
        ):
            redirect_uri = f"https://civic-signal-ai.vercel.app/api/auth/citizen/oauth/{provider}/callback"
            environment = {
                "CIVICSIGNAL_OAUTH_STATE_SECRET": state_secret,
                f"{prefix}_CLIENT_ID": f"{provider}-client-id",
                f"{prefix}_CLIENT_SECRET": f"{provider}-client-secret",
                f"{prefix}_REDIRECT_URI": redirect_uri,
            }
            with self.subTest(provider=provider), patch.dict(os.environ, environment):
                start = self.client.get(f"/api/auth/citizen/oauth/{provider}", follow_redirects=False)
                self.assertEqual(start.status_code, 302)
                authorization = urlparse(start.headers["location"])
                authorization_query = parse_qs(authorization.query)
                self.assertEqual(authorization_query["redirect_uri"][0], redirect_uri)
                self.assertEqual(authorization_query["code_challenge_method"][0], "S256")
                self.assertNotIn(f"{provider}-client-secret", start.headers["location"])
                state = authorization_query["state"][0]

                requests = []

                def mocked_urlopen(request, timeout):
                    requests.append(request)
                    if request.full_url.endswith("/token") or request.full_url.endswith("/accessToken"):
                        return OAuthResponse({"access_token": "server-only-access-token"})
                    return OAuthResponse({
                        "sub": subject,
                        "email": self.email,
                        "email_verified": True,
                    })

                callback_query = urlencode({"code": "authorization-code", "state": state})
                with patch("app.api.auth.urllib.request.urlopen", side_effect=mocked_urlopen):
                    callback = self.client.get(
                        f"/api/auth/citizen/oauth/{provider}/callback?{callback_query}",
                        follow_redirects=False,
                    )

                self.assertEqual(callback.status_code, 303)
                self.assertEqual(callback.headers["location"], "/home")
                self.assertEqual(len(requests), 2)
                token_form = parse_qs(requests[0].data.decode("utf-8"))
                self.assertEqual(token_form["client_secret"][0], f"{provider}-client-secret")
                self.assertEqual(token_form["redirect_uri"][0], redirect_uri)
                self.assertIn("code_verifier", token_form)
                self.assertEqual(requests[1].get_header("Authorization"), "Bearer server-only-access-token")
                self.assertEqual(self.client.get("/api/auth/citizen/me").status_code, 200)

    def test_oauth_rejects_state_mismatch_without_contacting_provider(self):
        environment = {
            "CIVICSIGNAL_OAUTH_STATE_SECRET": "test-oauth-state-secret-with-at-least-32-bytes",
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-client-secret",
            "GOOGLE_REDIRECT_URI": "https://civic-signal-ai.vercel.app/api/auth/citizen/oauth/google/callback",
        }
        with patch.dict(os.environ, environment):
            start = self.client.get("/api/auth/citizen/oauth/google", follow_redirects=False)
            state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
            with patch("app.api.auth.urllib.request.urlopen") as provider_request:
                callback = self.client.get(
                    f"/api/auth/citizen/oauth/google/callback?{urlencode({'code': 'code', 'state': state + 'x'})}",
                    follow_redirects=False,
                )

        self.assertEqual(callback.status_code, 303)
        self.assertIn("oauth_error=invalid_state", callback.headers["location"])
        provider_request.assert_not_called()

    def test_oauth_requires_configuration(self):
        with patch.dict(os.environ, {
            "CIVICSIGNAL_OAUTH_STATE_SECRET": "",
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GOOGLE_REDIRECT_URI": "",
        }):
            response = self.client.get("/api/auth/citizen/oauth/google", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertIn("oauth_error=not_configured", response.headers["location"])

    def test_oauth_requires_the_exact_provider_callback_path(self):
        with patch.dict(os.environ, {
            "CIVICSIGNAL_OAUTH_STATE_SECRET": "test-oauth-state-secret-with-at-least-32-bytes",
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-client-secret",
            "GOOGLE_REDIRECT_URI": "https://civic-signal-ai.vercel.app/wrong-callback",
        }):
            response = self.client.get("/api/auth/citizen/oauth/google", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertIn("oauth_error=not_configured", response.headers["location"])

    def test_oauth_does_not_create_an_account_for_a_new_provider_email(self):
        environment = {
            "CIVICSIGNAL_OAUTH_STATE_SECRET": "test-oauth-state-secret-with-at-least-32-bytes",
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-client-secret",
            "GOOGLE_REDIRECT_URI": "https://civic-signal-ai.vercel.app/api/auth/citizen/oauth/google/callback",
        }
        with patch.dict(os.environ, environment):
            start = self.client.get("/api/auth/citizen/oauth/google", follow_redirects=False)
            state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
            with patch("app.api.auth.urllib.request.urlopen", side_effect=[
                OAuthResponse({"access_token": "server-only-access-token"}),
                OAuthResponse({
                    "sub": "unregistered-subject",
                    "email": "new-citizen@example.test",
                    "email_verified": True,
                }),
            ]):
                callback = self.client.get(
                    f"/api/auth/citizen/oauth/google/callback?{urlencode({'code': 'code', 'state': state})}",
                    follow_redirects=False,
                )

        self.assertEqual(callback.status_code, 303)
        self.assertIn("oauth_error=account_required", callback.headers["location"])
        self.assertEqual(self.client.get("/api/auth/citizen/me").status_code, 401)

    def test_reports_are_private_to_their_citizen_and_admins_can_still_view_them(self):
        self.assertEqual(self.signup().status_code, 200)
        created = self.create_report()
        self.assertEqual(created.status_code, 201, created.text)
        report_id = created.json()["id"]
        own_tracking = self.client.get(f"/api/reports/{report_id}/tracking")
        self.assertEqual(own_tracking.status_code, 200)

        self.client.post("/api/auth/citizen/logout")
        self.assertEqual(self.signup("other@example.test").status_code, 200)
        other_tracking = self.client.get(f"/api/reports/{report_id}/tracking")
        self.assertEqual(other_tracking.status_code, 404)
        forbidden_update = self.client.patch(
            f"/api/team/reports/{report_id}/status",
            json={"status": "acknowledged"},
        )
        self.assertEqual(forbidden_update.status_code, 401)

        admin_login = self.client.post("/api/auth/team/login", json={
            "username": "test-admin",
            "password": "a-valid-admin-password",
        })
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(self.client.get(f"/api/reports/{report_id}/tracking").status_code, 200)
        self.assertEqual(self.client.get("/api/reports").status_code, 200)
