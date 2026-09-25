"""Integration tests for GET /api/v1/health."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the public health check endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_body(self, client: TestClient) -> None:
        """Health response should contain expected fields."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "environment" in data

    def test_health_service_name(self, client: TestClient) -> None:
        """Health response service name should match APP_NAME."""
        from app.core.config import get_settings

        settings = get_settings()
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["service"] == settings.app_name

    def test_health_no_auth_required(self, client: TestClient) -> None:
        """Health endpoint must not require Authorization header."""
        response = client.get("/api/v1/health")
        # Must not return 401
        assert response.status_code != 401

    def test_health_content_type_json(self, client: TestClient) -> None:
        """Health endpoint must return JSON content type."""
        response = client.get("/api/v1/health")
        assert "application/json" in response.headers.get("content-type", "")
