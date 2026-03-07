"""Tests for sentiment analysis."""

from herald.sentiment import analyze_sentiment, sentiment_label


def test_positive_message_scores_positive():
    """Positive words produce a positive score."""
    score = analyze_sentiment("This is great, I love your product! Excellent work!")
    assert score > 0


def test_negative_message_scores_negative():
    """Negative words produce a negative score."""
    score = analyze_sentiment("This is terrible and broken, I hate your service")
    assert score < 0


def test_neutral_message_near_zero():
    """Messages without sentiment words score near zero."""
    score = analyze_sentiment("I would like to know about your API documentation")
    assert score == 0.0


def test_empty_message():
    """Empty message returns 0.0."""
    assert analyze_sentiment("") == 0.0
    assert analyze_sentiment("   ") == 0.0


def test_mixed_sentiment():
    """Mixed positive and negative words."""
    # "great" is positive, "broken" is negative
    score = analyze_sentiment("The interface is great but the backend is broken")
    # Score should be near zero since there's one positive and one negative
    assert -0.5 <= score <= 0.5


def test_strong_positive():
    """Strongly positive message scores high."""
    score = analyze_sentiment("Awesome, perfect, excellent, love it, thank you so much!")
    assert score >= 0.5


def test_strong_negative():
    """Strongly negative message scores low."""
    score = analyze_sentiment("Terrible, awful, horrible, useless, worst experience ever")
    assert score <= -0.5


def test_sentiment_score_clamped():
    """Score is always between -1.0 and 1.0."""
    score = analyze_sentiment("great great great great amazing wonderful perfect")
    assert -1.0 <= score <= 1.0


def test_sentiment_label_very_negative():
    """Very negative score maps correctly."""
    assert sentiment_label(-0.8) == "very_negative"


def test_sentiment_label_neutral():
    """Near-zero score maps to neutral."""
    assert sentiment_label(0.0) == "neutral"
    assert sentiment_label(0.1) == "neutral"


def test_sentiment_label_positive():
    """Positive score maps correctly."""
    assert sentiment_label(0.5) == "positive"


def test_sentiment_label_very_positive():
    """Very positive score maps correctly."""
    assert sentiment_label(0.9) == "very_positive"
