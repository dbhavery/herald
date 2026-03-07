"""Ticket management — create, update, list, and auto-categorize."""

from datetime import datetime, timezone
from uuid import uuid4

from herald.database import get_connection

# Keywords used for auto-categorization
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bug": ["bug", "crash", "error", "broken", "not working", "fails", "glitch", "freeze"],
    "billing": ["billing", "invoice", "charge", "payment", "subscription", "refund", "price", "plan"],
    "feature": ["feature", "request", "suggestion", "wish", "would be nice", "add", "enhance"],
    "technical": ["api", "integration", "webhook", "sdk", "deploy", "server", "database", "config"],
}


def auto_categorize(text: str) -> str:
    """Determine ticket category from subject/description text.

    Args:
        text: The combined subject + description text.

    Returns:
        Category string: bug, billing, feature, technical, or general.
    """
    lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in lower)

    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        return best
    return "general"


def create_ticket(
    customer_id: str,
    subject: str,
    description: str | None = None,
    conversation_id: str | None = None,
    priority: str = "medium",
) -> dict:
    """Create a new support ticket.

    Args:
        customer_id: The customer who raised the ticket.
        subject: Short summary.
        description: Detailed description.
        conversation_id: Optional linked conversation.
        priority: low, medium, high, or urgent.

    Returns:
        The created ticket dict.
    """
    conn = get_connection()
    ticket_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    combined_text = subject
    if description:
        combined_text += " " + description
    category = auto_categorize(combined_text)

    conn.execute(
        """INSERT INTO tickets (id, conversation_id, customer_id, subject, description,
           status, priority, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)""",
        (ticket_id, conversation_id, customer_id, subject, description, priority, category, now, now),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row)


def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
) -> list[dict]:
    """List tickets with optional filters.

    Args:
        status: Filter by status.
        priority: Filter by priority.
        category: Filter by category.

    Returns:
        List of ticket dicts.
    """
    conn = get_connection()
    query = "SELECT * FROM tickets WHERE 1=1"
    params: list[str] = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_ticket(ticket_id: str) -> dict | None:
    """Get a single ticket by ID.

    Args:
        ticket_id: The ticket ID.

    Returns:
        Ticket dict or None.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def update_ticket(ticket_id: str, updates: dict) -> dict | None:
    """Update ticket fields.

    Args:
        ticket_id: The ticket ID.
        updates: Dict of field -> new value.

    Returns:
        Updated ticket dict or None if not found.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        return None

    allowed = {"status", "priority", "assigned_to", "resolution_notes", "category"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}

    if not filtered:
        return dict(row)

    now = datetime.now(timezone.utc).isoformat()
    filtered["updated_at"] = now

    # If resolving, set resolved_at
    if filtered.get("status") in ("resolved", "closed"):
        filtered["resolved_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [ticket_id]

    conn.execute(f"UPDATE tickets SET {set_clause} WHERE id = ?", values)
    conn.commit()

    updated = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(updated)
