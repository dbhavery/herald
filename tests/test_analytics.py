"""Tests for analytics endpoints."""


def test_overview_stats(client):
    """Overview returns all expected metric fields."""
    resp = client.get("/api/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_conversations" in data
    assert "avg_sentiment" in data
    assert "open_tickets" in data
    assert "at_risk_customers" in data
    assert isinstance(data["active_conversations"], int)
    assert isinstance(data["avg_sentiment"], float)


def test_overview_stats_accurate(client):
    """Overview stats match the seeded data."""
    data = client.get("/api/analytics/overview").json()
    # We have active conversations in seed data
    assert data["active_conversations"] >= 1
    # We have at-risk customers (cust_04 and cust_07 are high risk)
    assert data["at_risk_customers"] >= 2


def test_sentiment_trend(client):
    """Sentiment trend returns daily aggregates."""
    resp = client.get("/api/analytics/sentiment")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        entry = data[0]
        assert "date" in entry
        assert "avg_sentiment" in entry
        assert "conversation_count" in entry


def test_churn_analysis(client):
    """Churn analysis returns breakdown and at-risk list."""
    resp = client.get("/api/analytics/churn")
    assert resp.status_code == 200
    data = resp.json()
    assert "risk_breakdown" in data
    assert "at_risk_customers" in data
    breakdown = data["risk_breakdown"]
    assert "low" in breakdown
    assert "medium" in breakdown
    assert "high" in breakdown
    # Total customers should match
    total = breakdown["low"] + breakdown["medium"] + breakdown["high"]
    assert total == 8


def test_resolution_metrics(client):
    """Resolution metrics return time stats."""
    resp = client.get("/api/analytics/resolution")
    assert resp.status_code == 200
    data = resp.json()
    assert "avg_hours" in data
    assert "p50_hours" in data
    assert "p95_hours" in data
    assert "total_resolved" in data
    assert "by_category" in data
    # We have resolved tickets in seed data
    assert data["total_resolved"] >= 1


def test_resolution_by_category(client):
    """Resolution metrics include per-category breakdown."""
    data = client.get("/api/analytics/resolution").json()
    if data["by_category"]:
        for cat, stats in data["by_category"].items():
            assert "avg_hours" in stats
            assert "count" in stats
            assert stats["count"] >= 1
