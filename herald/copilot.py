"""Support rep copilot — generates response suggestions for agents."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from herald.database import get_connection
from herald.knowledge import search_knowledge

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:8b"

# Template responses keyed by detected topic
_TEMPLATES: dict[str, list[str]] = {
    "billing": [
        "I understand your concern about billing. Let me look into your account details and get this sorted out for you right away.",
        "Thank you for reaching out about your billing question. I can see your account here — let me review the charges and explain what happened.",
        "I'd be happy to help with your billing inquiry. Let me pull up your subscription details.",
    ],
    "bug": [
        "I'm sorry you're experiencing this issue. I've documented the problem and our engineering team will prioritize a fix. In the meantime, here's a workaround you can try.",
        "Thank you for reporting this bug. I can reproduce the issue on our end and have escalated it to our dev team. Can you share your browser/OS version for our records?",
        "I appreciate you letting us know about this. We take bugs seriously — I've created an internal ticket and we'll keep you updated on the fix.",
    ],
    "feature": [
        "That's a great suggestion! I've added this to our feature request board. Our product team reviews these regularly.",
        "Thank you for the feature request! I can see how this would improve your workflow. I'll make sure our product team sees this.",
        "I love that idea! While we don't have an ETA for this feature, I've logged your request and will keep you posted on any updates.",
    ],
    "technical": [
        "Let me help you with this technical issue. Based on what you've described, I'd recommend checking the API documentation for the latest endpoint specifications.",
        "I can assist with that technical question. Let me walk you through the configuration steps.",
        "Great question about the technical setup. Here's what I'd recommend based on our documentation and best practices.",
    ],
    "default": [
        "Thank you for contacting us! I'd be happy to help you with this. Could you provide a bit more detail so I can give you the best possible assistance?",
        "I appreciate you reaching out. Let me look into this for you and get back to you with a solution.",
        "Thanks for your patience! I'm reviewing your request and will have an answer for you shortly.",
    ],
}


def _detect_topic(messages: list[dict]) -> str:
    """Detect the primary topic from conversation messages.

    Args:
        messages: List of message dicts.

    Returns:
        Topic key matching _TEMPLATES.
    """
    all_text = " ".join(m["content"].lower() for m in messages)

    topic_keywords = {
        "billing": ["billing", "invoice", "charge", "payment", "subscription", "refund", "price"],
        "bug": ["bug", "crash", "error", "broken", "not working", "fails", "glitch"],
        "feature": ["feature", "request", "suggestion", "wish", "would like", "add"],
        "technical": ["api", "integration", "webhook", "sdk", "deploy", "config", "setup"],
    }

    scores = {}
    for topic, keywords in topic_keywords.items():
        scores[topic] = sum(1 for kw in keywords if kw in all_text)

    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        return best
    return "default"


def _call_ollama_for_suggestions(conversation_text: str, knowledge_context: str) -> list[str] | None:
    """Call Ollama to generate agent response suggestions.

    Args:
        conversation_text: Formatted conversation history.
        knowledge_context: Relevant knowledge base content.

    Returns:
        List of suggestion strings, or None if Ollama is unavailable.
    """
    prompt = (
        "You are a copilot for a customer support agent. Based on the conversation "
        "and knowledge base context below, generate exactly 3 suggested responses "
        "the agent could send to the customer. Each suggestion should be helpful, "
        "professional, and actionable.\n\n"
        f"=== Knowledge Base ===\n{knowledge_context}\n\n"
        f"=== Conversation ===\n{conversation_text}\n\n"
        "Generate 3 suggestions, each on a new line starting with a number:\n"
        "1. \n2. \n3. "
    )

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30.0,
        )
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            # Parse numbered suggestions
            suggestions = []
            for line in text.split("\n"):
                line = line.strip()
                if line and len(line) > 3:
                    # Remove leading number + dot/paren
                    for prefix in ["1.", "2.", "3.", "1)", "2)", "3)"]:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                            break
                    if line:
                        suggestions.append(line)
            if suggestions:
                return suggestions[:3]
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.info("Ollama unavailable (%s), using template suggestions", type(exc).__name__)

    return None


def generate_suggestions(conversation_id: str) -> dict:
    """Generate copilot suggestions for a conversation.

    1. Load conversation history
    2. Search knowledge base for relevant context
    3. Generate suggestions (Ollama or template fallback)
    4. Store suggestions in database

    Args:
        conversation_id: The conversation to generate suggestions for.

    Returns:
        Dict with suggestions list and context_used list.

    Raises:
        ValueError: If conversation not found.
    """
    conn = get_connection()

    # Load conversation
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Load messages
    messages = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    messages = [dict(m) for m in messages]

    if not messages:
        return {"suggestions": [], "context_used": []}

    # Search knowledge base using last customer message
    customer_messages = [m for m in messages if m["role"] == "customer"]
    search_query = customer_messages[-1]["content"] if customer_messages else messages[-1]["content"]
    knowledge_items = search_knowledge(search_query, top_k=3)

    # Format for LLM
    conversation_text = "\n".join(
        f"{'Customer' if m['role'] == 'customer' else 'Agent'}: {m['content']}"
        for m in messages[-8:]
    )
    knowledge_context = "\n".join(
        f"[{item['title']}]: {item['content']}" for item in knowledge_items
    )

    context_used = [item["title"] for item in knowledge_items]

    # Try Ollama first
    suggestions_text = _call_ollama_for_suggestions(conversation_text, knowledge_context)

    # Fallback to templates
    if not suggestions_text:
        topic = _detect_topic(messages)
        templates = _TEMPLATES.get(topic, _TEMPLATES["default"])
        suggestions_text = templates[:3]

    # Store suggestions in database
    now = datetime.now(timezone.utc).isoformat()
    suggestion_records = []
    for text in suggestions_text:
        sug_id = uuid4().hex
        conn.execute(
            "INSERT INTO copilot_suggestions (id, conversation_id, suggestion, used, created_at) VALUES (?, ?, ?, 0, ?)",
            (sug_id, conversation_id, text, now),
        )
        suggestion_records.append({"id": sug_id, "suggestion": text, "used": False})

    conn.commit()

    return {"suggestions": suggestion_records, "context_used": context_used}


def accept_suggestion(suggestion_id: str) -> dict | None:
    """Mark a copilot suggestion as used.

    Args:
        suggestion_id: The suggestion ID to accept.

    Returns:
        Updated suggestion dict, or None if not found.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM copilot_suggestions WHERE id = ?", (suggestion_id,)
    ).fetchone()
    if not row:
        return None

    conn.execute(
        "UPDATE copilot_suggestions SET used = 1 WHERE id = ?", (suggestion_id,)
    )
    conn.commit()

    updated = conn.execute(
        "SELECT * FROM copilot_suggestions WHERE id = ?", (suggestion_id,)
    ).fetchone()
    return dict(updated)
