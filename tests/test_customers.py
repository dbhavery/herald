"""Tests for customer management and health scoring."""

from herald.customers import compute_health_score, compute_churn_risk
from herald.database import get_connection


def test_list_customers(client):
    """List all seeded customers."""
    resp = client.get("/api/customers")
    assert resp.status_code == 200
    customers = resp.json()
    assert len(customers) == 8


def test_list_customers_filter_plan(client):
    """Filter customers by plan."""
    resp = client.get("/api/customers?plan=enterprise")
    assert resp.status_code == 200
    for c in resp.json():
        assert c["plan"] == "enterprise"


def test_list_customers_filter_churn_risk(client):
    """Filter customers by churn risk."""
    resp = client.get("/api/customers?churn_risk=high")
    assert resp.status_code == 200
    for c in resp.json():
        assert c["churn_risk"] == "high"


def test_get_customer_detail(client):
    """Get customer with recent conversations and open tickets."""
    resp = client.get("/api/customers/cust_01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sarah Chen"
    assert "recent_conversations" in data
    assert "open_tickets" in data


def test_get_customer_not_found(client):
    """Getting a non-existent customer returns 404."""
    resp = client.get("/api/customers/nonexistent")
    assert resp.status_code == 404


def test_update_customer(client):
    """Update customer fields."""
    resp = client.patch("/api/customers/cust_06", json={"plan": "starter", "company": "Freelance Inc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "starter"
    assert data["company"] == "Freelance Inc"


def test_health_score_calculation(client):
    """Health score components work correctly."""
    # cust_08: enterprise, very recently active, good sentiment
    score = compute_health_score("cust_08")
    assert score > 0
    # Enterprise plan gives +20
    assert score >= 20


def test_churn_risk_high():
    """Low health score maps to high churn risk."""
    assert compute_churn_risk(10) == "high"
    assert compute_churn_risk(39) == "high"


def test_churn_risk_medium():
    """Medium health score maps to medium churn risk."""
    assert compute_churn_risk(40) == "medium"
    assert compute_churn_risk(69) == "medium"


def test_churn_risk_low():
    """High health score maps to low churn risk."""
    assert compute_churn_risk(70) == "low"
    assert compute_churn_risk(100) == "low"
