"""Tests for ticket management."""

from herald.tickets import auto_categorize


def test_create_ticket(client):
    """Create a new ticket."""
    resp = client.post("/api/tickets", json={
        "customer_id": "cust_02",
        "subject": "Cannot login to dashboard",
        "description": "Getting an error when trying to login with my credentials"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == "cust_02"
    assert data["subject"] == "Cannot login to dashboard"
    assert data["status"] == "open"
    assert data["priority"] == "medium"
    assert data["category"] is not None


def test_list_tickets(client):
    """List all seeded tickets."""
    resp = client.get("/api/tickets")
    assert resp.status_code == 200
    tickets = resp.json()
    assert len(tickets) == 8


def test_filter_tickets_by_status(client):
    """Filter tickets by status."""
    resp = client.get("/api/tickets?status=open")
    assert resp.status_code == 200
    for t in resp.json():
        assert t["status"] == "open"


def test_filter_tickets_by_priority(client):
    """Filter tickets by priority."""
    resp = client.get("/api/tickets?priority=urgent")
    assert resp.status_code == 200
    for t in resp.json():
        assert t["priority"] == "urgent"


def test_update_ticket_status(client):
    """Update a ticket's status."""
    resp = client.patch("/api/tickets/tkt_01", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_update_ticket_resolve(client):
    """Resolving a ticket sets resolved_at."""
    resp = client.patch("/api/tickets/tkt_02", json={
        "status": "resolved",
        "resolution_notes": "Fixed CSP configuration"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None
    assert data["resolution_notes"] == "Fixed CSP configuration"


def test_auto_categorize_bug():
    """Auto-categorize detects bug-related text."""
    assert auto_categorize("The app keeps crashing when I click submit") == "bug"
    assert auto_categorize("There's an error on the login page") == "bug"


def test_auto_categorize_billing():
    """Auto-categorize detects billing-related text."""
    assert auto_categorize("I was charged twice on my invoice") == "billing"


def test_auto_categorize_feature():
    """Auto-categorize detects feature requests."""
    assert auto_categorize("I'd like to request a new feature for reports") == "feature"


def test_auto_categorize_general():
    """Auto-categorize falls back to general."""
    assert auto_categorize("Hello I have a question") == "general"
