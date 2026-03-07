"""Tests for the customer-facing chatbot."""

from herald.database import get_connection


def test_chat_returns_response(client):
    """Sending a message returns a response with conversation_id and sentiment."""
    resp = client.post("/api/chat", json={"customer_id": "cust_01", "message": "How do I set up webhooks?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "sentiment" in data
    assert len(data["response"]) > 0


def test_chat_creates_conversation(client):
    """Chat should create a conversation if none exists for the customer."""
    # Use a customer with no active conversations after resolving existing ones
    conn = get_connection()
    conn.execute("UPDATE conversations SET status = 'resolved' WHERE customer_id = 'cust_06'")
    conn.commit()

    resp = client.post("/api/chat", json={"customer_id": "cust_06", "message": "Hello, I need help"})
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    # Verify conversation was created
    conv_resp = client.get(f"/api/conversations/{conv_id}")
    assert conv_resp.status_code == 200
    assert conv_resp.json()["customer_id"] == "cust_06"


def test_chat_stores_messages(client):
    """Chat should store both customer message and bot response."""
    resp = client.post("/api/chat", json={"customer_id": "cust_02", "message": "What is your pricing?"})
    conv_id = resp.json()["conversation_id"]

    conv = client.get(f"/api/conversations/{conv_id}").json()
    messages = conv["messages"]

    # Should have at least the customer message and bot response from this exchange
    roles = [m["role"] for m in messages]
    assert "customer" in roles
    assert "bot" in roles


def test_chat_tracks_sentiment(client):
    """Chat should analyze and track sentiment on each message."""
    # Positive message
    resp = client.post("/api/chat", json={"customer_id": "cust_05", "message": "This is great, I love your product! Excellent work!"})
    assert resp.status_code == 200
    assert resp.json()["sentiment"] > 0

    # Negative message
    conn = get_connection()
    conn.execute("UPDATE conversations SET status = 'resolved' WHERE customer_id = 'cust_07'")
    conn.commit()
    resp = client.post("/api/chat", json={"customer_id": "cust_07", "message": "This is terrible and broken, I hate it"})
    assert resp.status_code == 200
    assert resp.json()["sentiment"] < 0


def test_list_conversations(client):
    """Listing conversations returns seeded data."""
    resp = client.get("/api/conversations")
    assert resp.status_code == 200
    convos = resp.json()
    assert len(convos) >= 8


def test_list_conversations_filter_status(client):
    """Filter conversations by status."""
    resp = client.get("/api/conversations?status=active")
    assert resp.status_code == 200
    for c in resp.json():
        assert c["status"] == "active"


def test_get_conversation_detail(client):
    """Get a specific conversation with messages."""
    resp = client.get("/api/conversations/conv_01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "conv_01"
    assert "messages" in data
    assert len(data["messages"]) >= 1
