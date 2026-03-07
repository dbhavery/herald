"""Product knowledge base — ingestion, storage, and TF-IDF search."""

import json
import math
import re
from datetime import datetime, timezone
from uuid import uuid4

from herald.database import get_connection


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _compute_tfidf(text: str, corpus_texts: list[str]) -> list[float]:
    """Compute a simple TF-IDF vector for *text* against *corpus_texts*.

    Returns a list of floats (one per unique term across the corpus).
    """
    corpus_token_sets = [set(_tokenize(t)) for t in corpus_texts]
    all_terms = sorted({term for tokens in corpus_token_sets for term in tokens})
    if not all_terms:
        return []

    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * len(all_terms)

    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    max_tf = max(tf.values()) if tf else 1
    for t in tf:
        tf[t] /= max_tf

    n_docs = len(corpus_texts) + 1  # +1 to avoid div-by-zero edge
    idf: dict[str, float] = {}
    for term in all_terms:
        doc_count = sum(1 for s in corpus_token_sets if term in s)
        idf[term] = math.log((n_docs + 1) / (doc_count + 1)) + 1

    vector = [tf.get(term, 0.0) * idf.get(term, 0.0) for term in all_terms]
    return vector


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors of the same length."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def add_knowledge_item(title: str, content: str, category: str) -> dict:
    """Insert a knowledge item into the database.

    Args:
        title: Short title for the knowledge item.
        content: Full text content.
        category: One of product, billing, technical, onboarding, faq.

    Returns:
        The created item as a dict.
    """
    conn = get_connection()
    item_id = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO knowledge_items (id, title, content, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (item_id, title, content, category, now, now),
    )
    conn.commit()
    return {
        "id": item_id,
        "title": title,
        "content": content,
        "category": category,
        "created_at": now,
        "updated_at": now,
    }


def list_knowledge_items(category: str | None = None) -> list[dict]:
    """List all knowledge items, optionally filtered by category.

    Args:
        category: If provided, only return items in this category.

    Returns:
        A list of knowledge item dicts.
    """
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM knowledge_items WHERE category = ? ORDER BY created_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM knowledge_items ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def search_knowledge(query: str, top_k: int = 5) -> list[dict]:
    """Search knowledge items using keyword matching and TF-IDF ranking.

    Args:
        query: The search query string.
        top_k: Maximum number of results to return.

    Returns:
        A list of dicts with id, title, content, score — sorted by relevance.
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM knowledge_items").fetchall()
    if not rows:
        return []

    items = [dict(r) for r in rows]
    corpus_texts = [f"{item['title']} {item['content']}" for item in items]

    query_vector = _compute_tfidf(query, corpus_texts)

    scored: list[tuple[float, dict]] = []
    for item, doc_text in zip(items, corpus_texts):
        doc_vector = _compute_tfidf(doc_text, corpus_texts)
        score = _cosine_similarity(query_vector, doc_vector)

        # Boost by direct keyword overlap
        query_tokens = set(_tokenize(query))
        doc_tokens = set(_tokenize(doc_text))
        overlap = len(query_tokens & doc_tokens)
        if query_tokens:
            keyword_boost = overlap / len(query_tokens) * 0.3
            score += keyword_boost

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, item in scored[:top_k]:
        if score > 0.0:
            results.append({
                "id": item["id"],
                "title": item["title"],
                "content": item["content"],
                "score": round(score, 4),
            })

    return results
