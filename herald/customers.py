"""Customer management — CRUD, health scoring, and churn risk."""

from datetime import datetime, timezone
from uuid import uuid4

from herald.database import get_connection


def _parse_dt(dt_str: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning None on failure."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def compute_health_score(customer_id: str) -> float:
    """Compute health score (0-100) for a customer.

    Components:
      - Recent activity: last_active within 7d = +30, 30d = +15, else 0
      - Conversation sentiment: avg sentiment * 20 (range -20 to +20)
      - Ticket resolution: -10 per unresolved ticket (max -30)
      - Plan value: enterprise=+20, pro=+15, starter=+10, free=+5

    Args:
        customer_id: The customer ID.

    Returns:
        Health score clamped to 0-100.
    """
    conn = get_connection()
    cust = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not cust:
        return 0.0

    score = 0.0
    now = datetime.now(timezone.utc)

    # --- Recent activity ---
    last_active = _parse_dt(cust["last_active"])
    if last_active:
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        days_since = (now - last_active).days
        if days_since <= 7:
            score += 30
        elif days_since <= 30:
            score += 15

    # --- Conversation sentiment ---
    sentiment_row = conn.execute(
        "SELECT AVG(sentiment_score) as avg_sent FROM conversations WHERE customer_id = ? AND sentiment_score IS NOT NULL",
        (customer_id,),
    ).fetchone()
    if sentiment_row and sentiment_row["avg_sent"] is not None:
        score += sentiment_row["avg_sent"] * 20  # range -20 to +20

    # --- Unresolved tickets ---
    unresolved = conn.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE customer_id = ? AND status NOT IN ('resolved', 'closed')",
        (customer_id,),
    ).fetchone()
    if unresolved:
        penalty = min(unresolved["cnt"] * 10, 30)
        score -= penalty

    # --- Plan value ---
    plan_scores = {"enterprise": 20, "pro": 15, "starter": 10, "free": 5}
    score += plan_scores.get(cust["plan"], 5)

    return max(0.0, min(100.0, score))


def compute_churn_risk(health_score: float) -> str:
    """Map health score to churn risk label.

    Args:
        health_score: A value from 0 to 100.

    Returns:
        "high", "medium", or "low".
    """
    if health_score < 40:
        return "high"
    elif health_score < 70:
        return "medium"
    return "low"


def refresh_customer_health(customer_id: str) -> dict | None:
    """Recompute and persist health score and churn risk for a customer.

    Args:
        customer_id: The customer ID.

    Returns:
        Updated customer dict or None if not found.
    """
    conn = get_connection()
    cust = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not cust:
        return None

    health = compute_health_score(customer_id)
    risk = compute_churn_risk(health)

    conn.execute(
        "UPDATE customers SET health_score = ?, churn_risk = ? WHERE id = ?",
        (health, risk, customer_id),
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    return dict(updated)


def list_customers(plan: str | None = None, churn_risk: str | None = None) -> list[dict]:
    """List customers with optional filters.

    Args:
        plan: Filter by plan name.
        churn_risk: Filter by churn risk level.

    Returns:
        List of customer dicts.
    """
    conn = get_connection()
    query = "SELECT * FROM customers WHERE 1=1"
    params: list[str] = []

    if plan:
        query += " AND plan = ?"
        params.append(plan)
    if churn_risk:
        query += " AND churn_risk = ?"
        params.append(churn_risk)

    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_customer(customer_id: str) -> dict | None:
    """Get a single customer by ID with computed stats.

    Args:
        customer_id: The customer ID.

    Returns:
        Customer dict with extra stats, or None.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not row:
        return None

    cust = dict(row)

    # Attach recent conversations
    convos = conn.execute(
        "SELECT * FROM conversations WHERE customer_id = ? ORDER BY created_at DESC LIMIT 10",
        (customer_id,),
    ).fetchall()
    cust["recent_conversations"] = [dict(c) for c in convos]

    # Attach open tickets
    tickets = conn.execute(
        "SELECT * FROM tickets WHERE customer_id = ? AND status NOT IN ('resolved', 'closed') ORDER BY created_at DESC",
        (customer_id,),
    ).fetchall()
    cust["open_tickets"] = [dict(t) for t in tickets]

    return cust


def update_customer(customer_id: str, updates: dict) -> dict | None:
    """Update customer fields.

    Args:
        customer_id: The customer ID.
        updates: Dict of field name -> new value (only non-None values applied).

    Returns:
        Updated customer dict, or None if not found.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not row:
        return None

    allowed = {"name", "email", "company", "plan", "health_score", "churn_risk", "last_active"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}

    if not filtered:
        return dict(row)

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [customer_id]

    conn.execute(f"UPDATE customers SET {set_clause} WHERE id = ?", values)
    conn.commit()

    updated = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    return dict(updated)


def create_customer(name: str, email: str, company: str | None = None, plan: str = "free") -> dict:
    """Create a new customer.

    Args:
        name: Customer's full name.
        email: Customer's email (must be unique).
        company: Optional company name.
        plan: Plan tier (free, starter, pro, enterprise).

    Returns:
        The created customer dict.
    """
    conn = get_connection()
    cust_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO customers (id, name, email, company, plan, health_score, signup_date, last_active, churn_risk, total_conversations, created_at)
           VALUES (?, ?, ?, ?, ?, 100.0, ?, ?, 'low', 0, ?)""",
        (cust_id, name, email, company, plan, now, now, now),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM customers WHERE id = ?", (cust_id,)).fetchone()
    return dict(row)
