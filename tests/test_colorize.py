"""Tests for colorization endpoints."""

import io

from fastapi.testclient import TestClient


class TestColorizeEndpoints:
    """Tests for colorization API endpoints."""

    def test_colorize_page(self, client: TestClient) -> None:
        """Test accessing the colorize page."""
        response = client.get("/colorize")
        assert response.status_code == 200
        assert "Leopa Color" in response.text
        assert "Colorize Infrared Image" in response.text

    def test_colorize_no_file(self, client: TestClient) -> None:
        """Test colorization without a file."""
        response = client.post(
            "/api/colorize",
            data={"reference_ids": "ref1"},
        )
        assert response.status_code == 422  # Validation error

    def test_colorize_no_references(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test colorization without reference IDs."""
        response = client.post(
            "/api/colorize",
            files={
                "file": ("infrared.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
            data={"reference_ids": ""},
        )
        # Empty string is interpreted as missing by FastAPI Form validation
        assert response.status_code == 422

    def test_colorize_invalid_reference(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test colorization with invalid reference ID."""
        response = client.post(
            "/api/colorize",
            files={
                "file": ("infrared.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
            data={"reference_ids": "nonexistent"},
        )
        assert response.status_code == 400
        assert "Reference image not found" in response.json()["detail"]

    def test_colorize_invalid_file_type(self, client: TestClient) -> None:
        """Test colorization with invalid file type."""
        response = client.post(
            "/api/colorize",
            files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
            data={"reference_ids": "ref1"},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_get_job_status_not_found(self, client: TestClient) -> None:
        """Test getting status of non-existent job."""
        response = client.get("/api/colorize/nonexistent")
        assert response.status_code == 404

    def test_get_job_result_not_found(self, client: TestClient) -> None:
        """Test getting result of non-existent job."""
        response = client.get("/api/colorize/nonexistent/result")
        assert response.status_code == 404


class TestColorizeIntegration:
    """Integration tests for colorization flow."""

    def test_colorize_starts_job(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test that colorization creates a job."""
        # First upload a reference
        ref_response = client.post(
            "/api/references",
            files={
                "file": ("reference.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
        )
        ref_id = ref_response.json()["id"]

        # Start colorization
        response = client.post(
            "/api/colorize",
            files={
                "file": ("infrared.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
            data={"reference_ids": ref_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["pending", "processing"]

    def test_colorize_job_status(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test checking job status after starting."""
        # First upload a reference
        ref_response = client.post(
            "/api/references",
            files={
                "file": ("reference.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
        )
        ref_id = ref_response.json()["id"]

        # Start colorization
        colorize_response = client.post(
            "/api/colorize",
            files={
                "file": ("infrared.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")
            },
            data={"reference_ids": ref_id},
        )
        job_id = colorize_response.json()["job_id"]

        # Check status
        status_response = client.get(f"/api/colorize/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        # Status could be pending, processing, completed, or failed depending on timing
        assert data["status"] in ["pending", "processing", "completed", "failed"]
