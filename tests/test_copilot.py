"""Tests for the support rep copilot."""


def test_suggestions_generated(client):
    """Copilot generates suggestions for a conversation."""
    resp = client.post("/api/copilot/suggest", json={"conversation_id": "conv_02"})
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) >= 1
    for s in data["suggestions"]:
        assert "id" in s
        assert "suggestion" in s
        assert len(s["suggestion"]) > 0


def test_suggestion_accepted(client):
    """Accepting a suggestion marks it as used."""
    # First generate suggestions
    resp = client.post("/api/copilot/suggest", json={"conversation_id": "conv_01"})
    suggestions = resp.json()["suggestions"]
    assert len(suggestions) >= 1

    sug_id = suggestions[0]["id"]

    # Accept it
    resp = client.post("/api/copilot/accept", json={"suggestion_id": sug_id})
    assert resp.status_code == 200
    assert resp.json()["used"] == 1


def test_suggestions_include_context(client):
    """Copilot suggestions include knowledge context used."""
    resp = client.post("/api/copilot/suggest", json={"conversation_id": "conv_01"})
    data = resp.json()
    assert "context_used" in data
    # context_used is a list of knowledge item titles
    assert isinstance(data["context_used"], list)


def test_suggestion_not_found(client):
    """Accepting a non-existent suggestion returns 404."""
    resp = client.post("/api/copilot/accept", json={"suggestion_id": "nonexistent"})
    assert resp.status_code == 404
