import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.team_auth import provision_team_user


class MediaWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "CIVICSIGNAL_DATABASE_PATH": str(root / "database.db"),
            "CIVICSIGNAL_UPLOAD_DIR": str(root / "private-media"),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client_context = TestClient(app, raise_server_exceptions=False)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.password = "valid-citizen-password"
        self.assertEqual(self.register("resident@example.test").status_code, 200)

    def register(self, email):
        return self.client.post("/api/auth/citizen/register", json={
            "full_name": "Test Resident",
            "email": email,
            "phone": "5551234567",
            "password": self.password,
            "confirm_password": self.password,
            "accepted_terms": True,
        })

    def create_report(self, **changes):
        payload = {
            "title": "Broken public light",
            "description": "The streetlight is out near the library.",
            "category": "broken_streetlight",
            "area": "Civic Center",
            "landmark": "Near the library",
        }
        payload.update(changes)
        return self.client.post("/api/reports", json=payload)

    @staticmethod
    def jpeg_bytes(color=(255, 0, 0)):
        image = Image.new("RGB", (8, 8), color)
        output = io.BytesIO()
        image.save(output, format="JPEG")
        return output.getvalue()

    def test_location_coordinates_must_be_a_confirmed_pair_and_are_persisted(self):
        missing_pair = self.create_report(latitude=40.7, location_confirmed=True)
        self.assertEqual(missing_pair.status_code, 422)

        unconfirmed = self.create_report(latitude=40.7, longitude=-74.0)
        self.assertEqual(unconfirmed.status_code, 422)

        invalid_range = self.create_report(latitude=91, longitude=-74.0, location_confirmed=True)
        self.assertEqual(invalid_range.status_code, 422)

        invalid_longitude = self.create_report(latitude=40.7, longitude=181, location_confirmed=True)
        self.assertEqual(invalid_longitude.status_code, 422)

        invalid_negative_longitude = self.create_report(latitude=40.7, longitude=-181, location_confirmed=True)
        self.assertEqual(invalid_negative_longitude.status_code, 422)

        created = self.create_report(
            category="drainage_waterlogging",
            latitude=40.7128,
            longitude=-74.006,
            location_confirmed=True,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["category"], "drainage_waterlogging")
        mine = self.client.get("/api/reports/mine").json()["reports"]
        saved = next(report for report in mine if report["id"] == created.json()["id"])
        self.assertAlmostEqual(saved["latitude"], 40.7128)
        self.assertAlmostEqual(saved["longitude"], -74.006)
        self.assertEqual(saved["area"], "Civic Center")

        boundary = self.create_report(latitude=-90, longitude=180, location_confirmed=True)
        self.assertEqual(boundary.status_code, 201, boundary.text)
        self.assertEqual(boundary.json()["latitude"], -90)
        self.assertEqual(boundary.json()["longitude"], 180)

    def test_citizen_uploads_real_private_photos_and_other_citizens_cannot_read_them(self):
        report = self.create_report()
        self.assertEqual(report.status_code, 201, report.text)
        report_id = report.json()["id"]
        image_bytes = self.jpeg_bytes()
        uploaded = self.client.post(
            f"/api/reports/{report_id}/images",
            files=[("files", ("unsafe-name.jpg", image_bytes, "image/jpeg"))],
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        photo = uploaded.json()["images"][0]
        self.assertNotIn("storage_path", photo)
        stored_image = self.client.get(photo["url"])
        self.assertEqual(stored_image.status_code, 200)
        self.assertEqual(stored_image.headers["content-type"], "image/jpeg")
        self.assertTrue(stored_image.content.startswith(b"\xff\xd8"))

        invalid = self.client.post(
            f"/api/reports/{report_id}/images",
            files=[("files", ("fake.jpg", b"not an image", "image/jpeg"))],
        )
        self.assertEqual(invalid.status_code, 400)

        self.client.post("/api/auth/citizen/logout")
        self.assertEqual(self.register("other@example.test").status_code, 200)
        self.assertEqual(self.client.get(photo["url"]).status_code, 404)
        self.assertEqual(self.client.get(f"/api/reports/{report_id}/tracking").status_code, 404)

        unauthorized_upload = self.client.post(
            f"/api/reports/{report_id}/images",
            files=[("files", ("fake.jpg", b"not an image", "image/jpeg"))],
        )
        self.assertEqual(unauthorized_upload.status_code, 404)

    def test_only_admin_can_add_status_notes_and_progress_photos(self):
        report = self.create_report()
        report_id = report.json()["id"]
        progress_image = self.jpeg_bytes((0, 120, 255))

        denied = self.client.post(
            f"/api/team/reports/{report_id}/updates",
            data={"status": "under_review", "message": "Reviewing"},
        )
        self.assertEqual(denied.status_code, 401)

        self.client.post("/api/auth/citizen/logout")
        provision_team_user("staff@city.test", "valid-admin-password")
        login = self.client.post("/api/auth/team/login", json={
            "email": "staff@city.test",
            "password": "valid-admin-password",
        })
        self.assertEqual(login.status_code, 200)

        review = self.client.post(
            f"/api/team/reports/{report_id}/updates",
            data={"status": "under_review", "message": "Inspection completed."},
        )
        self.assertEqual(review.status_code, 200, review.text)
        progress = self.client.post(
            f"/api/team/reports/{report_id}/updates",
            data={"status": "in_progress", "message": "Repair work has started."},
            files=[("files", ("progress.webp", progress_image, "image/jpeg"))],
        )
        self.assertEqual(progress.status_code, 200, progress.text)

        rejection_without_reason = self.client.post(
            f"/api/team/reports/{report_id}/updates",
            data={"status": "rejected", "message": ""},
        )
        self.assertEqual(rejection_without_reason.status_code, 409)
        rejected = self.client.post(
            f"/api/team/reports/{report_id}/updates",
            data={"status": "rejected", "message": "Outside municipal jurisdiction."},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)

        tracking = self.client.get(f"/api/reports/{report_id}/tracking").json()
        self.assertEqual(tracking["report"]["status"], "rejected")
        self.assertTrue(any("Repair work has started" in event["message"] for event in tracking["timeline"]))
        self.assertTrue(any(image["media_type"] == "progress" for image in tracking["images"]))
        progress_photo = next(image for image in tracking["images"] if image["media_type"] == "progress")
        self.assertEqual(self.client.get(progress_photo["url"]).status_code, 200)
        self.client.post("/api/auth/team/logout")
        citizen_login = self.client.post("/api/auth/citizen/login", json={
            "email": "resident@example.test",
            "password": self.password,
        })
        self.assertEqual(citizen_login.status_code, 200)
        citizen_tracking = self.client.get(f"/api/reports/{report_id}/tracking")
        self.assertEqual(citizen_tracking.status_code, 200)
        self.assertTrue(any(image["media_type"] == "progress" for image in citizen_tracking.json()["images"]))
        self.assertEqual(self.client.get(progress_photo["url"]).status_code, 200)
