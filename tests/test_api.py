import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "EvalOS API"
    assert "docs" in response.json()

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_playground_validation_missing_key():
    """Test that missing API key results in a 422 validation error."""
    response = client.post("/api/playground", json={"question": "test"})
    assert response.status_code == 422

def test_playground_validation_long_question():
    """Test that a question > 500 chars results in a 422 validation error."""
    long_question = "a" * 501
    response = client.post("/api/playground", json={"api_key": "test", "question": long_question})
    assert response.status_code == 422
