"""Customer-facing AI chatbot — processes messages, searches knowledge, generates responses."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from herald.database import get_connection
from herald.knowledge import search_knowledge
from herald.sentiment import analyze_sentiment
from herald.tickets import create_ticket

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:8b"


def _get_or_create_conversation(customer_id: str) -> str:
    """Find an active conversation for the customer, or create one.

    Args:
        customer_id: The customer ID.

    Returns:
        Conversation ID.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM conversations WHERE customer_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
        (customer_id,),
    ).fetchone()

    if row:
        return row["id"]

    conv_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO conversations (id, customer_id, channel, status, created_at)
           VALUES (?, ?, 'chat', 'active', ?)""",
        (conv_id, customer_id, now),
    )
    conn.commit()

    # Increment customer's total_conversations
    conn.execute(
        "UPDATE customers SET total_conversations = total_conversations + 1, last_active = ? WHERE id = ?",
        (now, customer_id),
    )
    conn.commit()

    return conv_id


def _get_conversation_history(conversation_id: str, limit: int = 10) -> list[dict]:
    """Load recent messages for a conversation.

    Args:
        conversation_id: The conversation ID.
        limit: Max messages to return.

    Returns:
        List of message dicts ordered oldest first.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
        (conversation_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _save_message(conversation_id: str, role: str, content: str) -> dict:
    """Save a message to the database.

    Args:
        conversation_id: The conversation ID.
        role: "customer", "bot", or "agent".
        content: Message text.

    Returns:
        The saved message dict.
    """
    conn = get_connection()
    msg_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, conversation_id, role, content, now),
    )
    conn.commit()
    return {"id": msg_id, "conversation_id": conversation_id, "role": role, "content": content, "created_at": now}


def _update_conversation_sentiment(conversation_id: str, sentiment: float) -> None:
    """Update the running sentiment score on a conversation.

    Args:
        conversation_id: The conversation ID.
        sentiment: Latest sentiment score.
    """
    conn = get_connection()
    # Use exponential moving average: new = 0.3 * latest + 0.7 * existing
    existing = conn.execute(
        "SELECT sentiment_score FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()

    if existing and existing["sentiment_score"] is not None:
        new_score = 0.3 * sentiment + 0.7 * existing["sentiment_score"]
    else:
        new_score = sentiment

    conn.execute(
        "UPDATE conversations SET sentiment_score = ? WHERE id = ?",
        (new_score, conversation_id),
    )
    conn.commit()


def _build_prompt(message: str, knowledge_items: list[dict], history: list[dict]) -> str:
    """Build the LLM prompt from knowledge context and conversation history.

    Args:
        message: The latest customer message.
        knowledge_items: Relevant knowledge base items.
        history: Previous messages in the conversation.

    Returns:
        Formatted prompt string.
    """
    parts = [
        "You are Herald, a friendly and knowledgeable customer support assistant.",
        "Answer the customer's question using the provided knowledge base context.",
        "Be concise, helpful, and professional. If you don't know the answer, say so honestly.",
        "",
    ]

    if knowledge_items:
        parts.append("=== Knowledge Base Context ===")
        for item in knowledge_items:
            parts.append(f"[{item['title']}]: {item['content']}")
        parts.append("")

    if history:
        parts.append("=== Conversation History ===")
        for msg in history[-6:]:
            role_label = "Customer" if msg["role"] == "customer" else "Herald"
            parts.append(f"{role_label}: {msg['content']}")
        parts.append("")

    parts.append(f"Customer: {message}")
    parts.append("Herald:")

    return "\n".join(parts)


def _call_ollama(prompt: str) -> str | None:
    """Call Ollama API for LLM response.

    Args:
        prompt: The full prompt to send.

    Returns:
        Generated response text, or None if Ollama is unavailable.
    """
    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.info("Ollama unavailable (%s), using fallback response", type(exc).__name__)
    return None


def _mock_response(message: str, knowledge_items: list[dict]) -> str:
    """Generate a fallback response when Ollama is unavailable.

    Constructs a response from knowledge base excerpts.

    Args:
        message: The customer's message.
        knowledge_items: Relevant knowledge base items.

    Returns:
        A constructed response string.
    """
    if not knowledge_items:
        return (
            "Thank you for reaching out! I don't have specific information about that topic "
            "in my knowledge base right now. Let me connect you with a support agent who can help. "
            "Is there anything else I can assist with?"
        )

    best = knowledge_items[0]
    response_parts = [f"Based on our documentation about **{best['title']}**:"]

    # Take a relevant excerpt (first 200 chars of content)
    excerpt = best["content"]
    if len(excerpt) > 200:
        excerpt = excerpt[:200].rsplit(" ", 1)[0] + "..."
    response_parts.append(f"\n{excerpt}")

    if len(knowledge_items) > 1:
        response_parts.append(
            f"\n\nI also found related information in: {', '.join(item['title'] for item in knowledge_items[1:3])}."
        )

    response_parts.append("\n\nWould you like more details on any of these topics?")

    return "\n".join(response_parts)


def process_message(customer_id: str, message: str) -> dict:
    """Process an incoming customer message end-to-end.

    1. Get or create conversation
    2. Search knowledge base
    3. Build prompt with context
    4. Generate response (Ollama or mock)
    5. Analyze sentiment
    6. Save messages
    7. Auto-create ticket if very negative

    Args:
        customer_id: The customer's ID.
        message: The customer's message text.

    Returns:
        Dict with response, conversation_id, and sentiment score.
    """
    # Step 1: Get or create conversation
    conversation_id = _get_or_create_conversation(customer_id)

    # Step 2: Search knowledge base
    knowledge_items = search_knowledge(message, top_k=3)

    # Step 3: Get conversation history
    history = _get_conversation_history(conversation_id)

    # Step 4: Save customer message
    _save_message(conversation_id, "customer", message)

    # Step 5: Generate response
    prompt = _build_prompt(message, knowledge_items, history)
    response = _call_ollama(prompt)
    if response is None:
        response = _mock_response(message, knowledge_items)

    # Step 6: Save bot response
    _save_message(conversation_id, "bot", response)

    # Step 7: Analyze sentiment
    sentiment = analyze_sentiment(message)
    _update_conversation_sentiment(conversation_id, sentiment)

    # Step 8: Auto-create ticket if very negative
    if sentiment <= -0.5:
        create_ticket(
            customer_id=customer_id,
            subject=f"Auto-ticket: Negative sentiment detected",
            description=f"Customer message: {message[:500]}",
            conversation_id=conversation_id,
            priority="high",
        )

    return {
        "response": response,
        "conversation_id": conversation_id,
        "sentiment": sentiment,
    }


def list_conversations(status: str | None = None, customer_id: str | None = None) -> list[dict]:
    """List conversations with optional filters.

    Args:
        status: Filter by status.
        customer_id: Filter by customer.

    Returns:
        List of conversation dicts.
    """
    conn = get_connection()
    query = "SELECT c.*, cu.name as customer_name FROM conversations c LEFT JOIN customers cu ON c.customer_id = cu.id WHERE 1=1"
    params: list[str] = []

    if status:
        query += " AND c.status = ?"
        params.append(status)
    if customer_id:
        query += " AND c.customer_id = ?"
        params.append(customer_id)

    query += " ORDER BY c.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation with all its messages.

    Args:
        conversation_id: The conversation ID.

    Returns:
        Conversation dict with messages list, or None.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT c.*, cu.name as customer_name FROM conversations c LEFT JOIN customers cu ON c.customer_id = cu.id WHERE c.id = ?",
        (conversation_id,),
    ).fetchone()
    if not row:
        return None

    conv = dict(row)
    messages = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    conv["messages"] = [dict(m) for m in messages]
    return conv
