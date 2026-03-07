"""Onboarding flow management — create flows, track customer progress."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from herald.database import get_connection


def list_flows() -> list[dict]:
    """List all onboarding flows.

    Returns:
        List of flow dicts with steps_json parsed into steps list.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM onboarding_flows WHERE active = 1 ORDER BY created_at DESC"
    ).fetchall()

    results = []
    for r in rows:
        flow = dict(r)
        flow["steps"] = json.loads(flow["steps_json"])
        results.append(flow)
    return results


def get_flow(flow_id: str) -> dict | None:
    """Get a single onboarding flow.

    Args:
        flow_id: The flow ID.

    Returns:
        Flow dict with parsed steps, or None.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM onboarding_flows WHERE id = ?", (flow_id,)).fetchone()
    if not row:
        return None
    flow = dict(row)
    flow["steps"] = json.loads(flow["steps_json"])
    return flow


def start_onboarding(customer_id: str, flow_id: str) -> dict:
    """Start an onboarding flow for a customer.

    Args:
        customer_id: The customer to onboard.
        flow_id: The flow to start.

    Returns:
        The customer_onboarding record as a dict.

    Raises:
        ValueError: If the flow doesn't exist.
    """
    conn = get_connection()

    # Verify flow exists
    flow = conn.execute("SELECT * FROM onboarding_flows WHERE id = ?", (flow_id,)).fetchone()
    if not flow:
        raise ValueError(f"Onboarding flow {flow_id} not found")

    record_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO customer_onboarding (id, customer_id, flow_id, current_step, completed, started_at)
           VALUES (?, ?, ?, 0, 0, ?)""",
        (record_id, customer_id, flow_id, now),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM customer_onboarding WHERE id = ?", (record_id,)).fetchone()
    result = dict(row)

    # Attach flow details
    result["flow"] = dict(flow)
    result["flow"]["steps"] = json.loads(flow["steps_json"])
    return result


def complete_step(onboarding_id: str, step_index: int) -> dict | None:
    """Mark a step as completed in a customer's onboarding.

    Args:
        onboarding_id: The customer_onboarding record ID.
        step_index: The index of the step to mark completed.

    Returns:
        Updated customer_onboarding record, or None if not found.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customer_onboarding WHERE id = ?", (onboarding_id,)
    ).fetchone()
    if not row:
        return None

    record = dict(row)
    flow = conn.execute(
        "SELECT * FROM onboarding_flows WHERE id = ?", (record["flow_id"],)
    ).fetchone()
    if not flow:
        return None

    steps = json.loads(flow["steps_json"])
    total_steps = len(steps)

    new_step = step_index + 1
    completed = 1 if new_step >= total_steps else 0
    completed_at = datetime.now(timezone.utc).isoformat() if completed else None

    conn.execute(
        """UPDATE customer_onboarding SET current_step = ?, completed = ?, completed_at = ?
           WHERE id = ?""",
        (new_step, completed, completed_at, onboarding_id),
    )
    conn.commit()

    updated = conn.execute(
        "SELECT * FROM customer_onboarding WHERE id = ?", (onboarding_id,)
    ).fetchone()
    result = dict(updated)
    result["flow"] = dict(flow)
    result["flow"]["steps"] = steps
    return result


def get_customer_onboarding(customer_id: str) -> list[dict]:
    """Get all onboarding records for a customer.

    Args:
        customer_id: The customer ID.

    Returns:
        List of onboarding record dicts with flow details.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT co.*, of.name as flow_name, of.steps_json
           FROM customer_onboarding co
           JOIN onboarding_flows of ON co.flow_id = of.id
           WHERE co.customer_id = ?
           ORDER BY co.started_at DESC""",
        (customer_id,),
    ).fetchall()

    results = []
    for r in rows:
        record = dict(r)
        record["steps"] = json.loads(record["steps_json"])
        del record["steps_json"]
        results.append(record)
    return results
