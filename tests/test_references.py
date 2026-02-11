"""Tests for reference image endpoints."""

import io

from fastapi.testclient import TestClient


class TestReferenceEndpoints:
    """Tests for reference image API endpoints."""

    def test_list_references_empty(self, client: TestClient) -> None:
        """Test listing references when none exist."""
        response = client.get("/api/references")
        assert response.status_code == 200
        data = response.json()
        assert data["references"] == []

    def test_upload_reference(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test uploading a reference image."""
        response = client.post(
            "/api/references",
            files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.jpg"
        assert "id" in data
        assert data["url"].startswith("/data/references/")

    def test_upload_reference_invalid_type(self, client: TestClient) -> None:
        """Test uploading an invalid file type."""
        response = client.post(
            "/api/references",
            files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_list_references_after_upload(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test listing references after upload."""
        # Upload first
        client.post(
            "/api/references",
            files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
        )

        # List
        response = client.get("/api/references")
        assert response.status_code == 200
        data = response.json()
        assert len(data["references"]) == 1
        assert data["references"][0]["filename"] == "test.jpg"

    def test_get_reference(self, client: TestClient, sample_image_bytes: bytes) -> None:
        """Test getting a specific reference."""
        # Upload first
        upload_response = client.post(
            "/api/references",
            files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
        )
        ref_id = upload_response.json()["id"]

        # Get
        response = client.get(f"/api/references/{ref_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ref_id
        assert data["filename"] == "test.jpg"

    def test_get_reference_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent reference."""
        response = client.get("/api/references/nonexistent")
        assert response.status_code == 404

    def test_delete_reference(
        self, client: TestClient, sample_image_bytes: bytes
    ) -> None:
        """Test deleting a reference image."""
        # Upload first
        upload_response = client.post(
            "/api/references",
            files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
        )
        ref_id = upload_response.json()["id"]

        # Delete
        response = client.delete(f"/api/references/{ref_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/references/{ref_id}")
        assert response.status_code == 404

    def test_delete_reference_not_found(self, client: TestClient) -> None:
        """Test deleting a non-existent reference."""
        response = client.delete("/api/references/nonexistent")
        assert response.status_code == 404
