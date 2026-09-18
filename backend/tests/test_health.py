"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verifies that GET /api/v1/health returns HTTP 200 with expected payload."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "darukaa-biodiversity-intelligence"
