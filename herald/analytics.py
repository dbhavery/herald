"""Analytics — churn prediction, sentiment trends, resolution metrics."""

from datetime import datetime, timedelta, timezone

from herald.database import get_connection


def get_overview() -> dict:
    """Get key metrics overview.

    Returns:
        Dict with active_conversations, avg_sentiment, open_tickets, at_risk_customers.
    """
    conn = get_connection()

    active_convos = conn.execute(
        "SELECT COUNT(*) as cnt FROM conversations WHERE status = 'active'"
    ).fetchone()["cnt"]

    avg_sentiment_row = conn.execute(
        "SELECT AVG(sentiment_score) as avg_sent FROM conversations WHERE sentiment_score IS NOT NULL"
    ).fetchone()
    avg_sentiment = round(avg_sentiment_row["avg_sent"], 3) if avg_sentiment_row["avg_sent"] is not None else 0.0

    open_tickets = conn.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE status NOT IN ('resolved', 'closed')"
    ).fetchone()["cnt"]

    at_risk = conn.execute(
        "SELECT COUNT(*) as cnt FROM customers WHERE churn_risk = 'high'"
    ).fetchone()["cnt"]

    return {
        "active_conversations": active_convos,
        "avg_sentiment": avg_sentiment,
        "open_tickets": open_tickets,
        "at_risk_customers": at_risk,
    }


def get_sentiment_trend(days: int = 30) -> list[dict]:
    """Get daily average sentiment for the last N days.

    Args:
        days: Number of days to look back.

    Returns:
        List of dicts with date and avg_sentiment.
    """
    conn = get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    rows = conn.execute(
        """SELECT DATE(created_at) as date, AVG(sentiment_score) as avg_sentiment, COUNT(*) as count
           FROM conversations
           WHERE created_at >= ? AND sentiment_score IS NOT NULL
           GROUP BY DATE(created_at)
           ORDER BY date ASC""",
        (cutoff,),
    ).fetchall()

    return [
        {
            "date": r["date"],
            "avg_sentiment": round(r["avg_sentiment"], 3) if r["avg_sentiment"] is not None else 0.0,
            "conversation_count": r["count"],
        }
        for r in rows
    ]


def get_churn_analysis() -> dict:
    """Get churn risk breakdown and list of at-risk customers.

    Returns:
        Dict with risk_breakdown (counts) and at_risk_customers (list).
    """
    conn = get_connection()

    breakdown = {}
    for risk in ("low", "medium", "high"):
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM customers WHERE churn_risk = ?", (risk,)
        ).fetchone()["cnt"]
        breakdown[risk] = count

    at_risk = conn.execute(
        """SELECT id, name, email, company, plan, health_score, churn_risk, last_active
           FROM customers
           WHERE churn_risk IN ('high', 'medium')
           ORDER BY health_score ASC"""
    ).fetchall()

    return {
        "risk_breakdown": breakdown,
        "at_risk_customers": [dict(r) for r in at_risk],
    }


def get_resolution_metrics() -> dict:
    """Get ticket resolution time statistics.

    Returns:
        Dict with avg_hours, p50_hours, p95_hours, and by_category breakdown.
    """
    conn = get_connection()

    resolved = conn.execute(
        """SELECT category, created_at, resolved_at
           FROM tickets
           WHERE resolved_at IS NOT NULL AND status IN ('resolved', 'closed')"""
    ).fetchall()

    if not resolved:
        return {
            "avg_hours": 0.0,
            "p50_hours": 0.0,
            "p95_hours": 0.0,
            "total_resolved": 0,
            "by_category": {},
        }

    resolution_times: list[float] = []
    by_category: dict[str, list[float]] = {}

    for r in resolved:
        try:
            created = datetime.fromisoformat(r["created_at"])
            resolved_at = datetime.fromisoformat(r["resolved_at"])
            hours = (resolved_at - created).total_seconds() / 3600
            resolution_times.append(hours)

            cat = r["category"] or "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(hours)
        except (ValueError, TypeError):
            continue

    if not resolution_times:
        return {
            "avg_hours": 0.0,
            "p50_hours": 0.0,
            "p95_hours": 0.0,
            "total_resolved": 0,
            "by_category": {},
        }

    resolution_times.sort()
    n = len(resolution_times)

    avg = sum(resolution_times) / n
    p50 = resolution_times[n // 2]
    p95_idx = min(int(n * 0.95), n - 1)
    p95 = resolution_times[p95_idx]

    category_stats = {}
    for cat, times in by_category.items():
        times.sort()
        category_stats[cat] = {
            "avg_hours": round(sum(times) / len(times), 2),
            "count": len(times),
        }

    return {
        "avg_hours": round(avg, 2),
        "p50_hours": round(p50, 2),
        "p95_hours": round(p95, 2),
        "total_resolved": n,
        "by_category": category_stats,
    }
