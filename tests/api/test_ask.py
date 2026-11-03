import pytest
from fastapi.testclient import TestClient

from app.api.models import RetrievedChunk
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ask_returns_chunks(client, monkeypatch):
    # Mock the heavy retrieval function
    def fake_search_chunks(repo, question, top_k):
        assert repo == "psf/requests"
        assert question == "how does session send?"
        return [
            RetrievedChunk(
                path="src/requests/sessions.py",
                start_line=579,
                end_line=614,
                text="def send(self, request, **kwargs): ...",
                similarity=0.85,
            )
        ]

    monkeypatch.setattr("app.main.search_chunks", fake_search_chunks)

    response = client.post(
        "/ask",
        json={"repo": "psf/requests", "question": "how does session send?", "top_k": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repo"] == "psf/requests"
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["path"] == "src/requests/sessions.py"
    assert data["chunks"][0]["similarity"] == 0.85


def test_ask_validates_input(client):
    # Pydantic should reject a question that is too short
    response = client.post("/ask", json={"repo": "psf/requests", "question": "hi"})
    assert response.status_code == 422
    assert "at least 3 characters" in response.text


def test_ask_returns_404_on_empty_results(client, monkeypatch):
    monkeypatch.setattr("app.main.search_chunks", lambda *a, **kw: [])

    response = client.post(
        "/ask", json={"repo": "unknown/repo", "question": "where is the code"}
    )
    assert response.status_code == 404
    assert "No indexed chunks found" in response.json()["detail"]
