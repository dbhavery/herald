"""Keyword-based sentiment analysis for customer messages."""

import re

POSITIVE_WORDS: set[str] = {
    "thank", "thanks", "great", "love", "helpful", "perfect", "awesome",
    "excellent", "amazing", "wonderful", "fantastic", "appreciate",
    "happy", "pleased", "good", "nice", "brilliant", "superb",
    "outstanding", "impressive", "satisfied", "delighted",
}

NEGATIVE_WORDS: set[str] = {
    "frustrated", "angry", "terrible", "broken", "unacceptable", "worst",
    "hate", "awful", "horrible", "disgusting", "useless", "pathetic",
    "annoying", "disappointing", "furious", "ridiculous", "fail",
    "failed", "bug", "crash", "error", "problem", "issue", "wrong",
    "slow", "bad", "poor", "ugly",
}


def analyze_sentiment(text: str) -> float:
    """Analyze sentiment of text and return score from -1.0 to 1.0.

    Uses a simple keyword-matching approach:
      - Count positive and negative word occurrences
      - Score = (positive - negative) / (positive + negative)
      - Returns 0.0 if no sentiment words found

    Args:
        text: The text to analyze.

    Returns:
        A float from -1.0 (very negative) to 1.0 (very positive).
    """
    if not text or not text.strip():
        return 0.0

    words = set(re.findall(r"[a-z]+", text.lower()))

    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)

    total = positive_count + negative_count
    if total == 0:
        return 0.0

    score = (positive_count - negative_count) / total
    return max(-1.0, min(1.0, score))


def sentiment_label(score: float) -> str:
    """Convert a sentiment score to a human-readable label.

    Args:
        score: Sentiment score from -1.0 to 1.0.

    Returns:
        One of: "very_negative", "negative", "neutral", "positive", "very_positive".
    """
    if score <= -0.6:
        return "very_negative"
    elif score <= -0.2:
        return "negative"
    elif score <= 0.2:
        return "neutral"
    elif score <= 0.6:
        return "positive"
    else:
        return "very_positive"
