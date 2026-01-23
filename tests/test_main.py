"""Tests for the main application."""

from fastapi.testclient import TestClient

from leopa_color.main import app

client = TestClient(app)


def test_index() -> None:
    """Test the index page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Leopa Color Demo" in response.text


def test_get_color_red() -> None:
    """Test getting red color."""
    response = client.get("/color/red")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "red"
    assert data["hex"] == "#FF0000"


def test_get_color_unknown() -> None:
    """Test getting unknown color."""
    response = client.get("/color/unknown")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "unknown"
    assert data["hex"] == "#000000"
