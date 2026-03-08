# Herald

Customer operations platform that unifies AI chat support, agent copilot tooling, and predictive analytics into a single API -- cutting support response times from minutes to seconds with citation-backed answers.

## Why I Built This

Support teams drown in repetitive questions that already have answers buried in knowledge bases. Meanwhile, customer health degrades silently because sentiment, ticket volume, and engagement data live in separate silos. Herald connects these signals: the chatbot resolves questions instantly from existing documentation, the copilot accelerates human agents, and the analytics engine surfaces at-risk accounts before they churn.

## What It Does

- **AI chatbot with citations** -- retrieves relevant knowledge base articles via TF-IDF search, generates responses grounded in source material, and auto-creates tickets when sentiment drops below threshold
- **Support copilot** -- generates three ranked response suggestions per conversation by combining knowledge context with topic detection; agents accept with one click
- **Customer health scoring** -- aggregates 5 signals (sentiment trend, ticket frequency, resolution time, engagement recency, plan tier) into a 0-100 score mapped to risk tiers
- **Churn prediction** -- identifies at-risk accounts from health scores and surfaces them with breakdown dashboards for proactive outreach
- **Real-time sentiment tracking** -- keyword-based scoring (-1.0 to +1.0) with exponential moving average per conversation, powering auto-escalation and trend analytics

## Architecture

```
                     FastAPI (herald/main.py)
                            |
       +----------+---------+---------+----------+
       |          |         |         |          |
    Chatbot   Copilot  Customers  Tickets   Analytics
       |          |         |         |          |
       +----+-----+---------+---------+----------+
            |                         |
       Knowledge Base            Sentiment
       (TF-IDF search)          (keyword scoring)
            |                         |
            +-----------+-------------+
                        |
                  SQLite (WAL mode)
                  8 tables, FK enforced
```

The chatbot and copilot both query the knowledge base for context before generating responses. Sentiment scores feed back into customer health calculations and analytics aggregations. Ollama provides LLM generation when available; the system degrades gracefully with template-based fallbacks when it is not.

## Key Technical Decisions

- **SQLite over PostgreSQL** -- single-tenant deployment targeting demo and small-team use. WAL mode gives concurrent read performance. Zero ops overhead, sub-millisecond queries for the expected data volume. Trade-off: no horizontal scaling, but that is not a requirement.
- **TF-IDF for search over embedding-based retrieval** -- explainable relevance scoring (you can inspect which terms matched and why), no ML model dependency, instant indexing on document add. Trade-off: misses semantic similarity that embeddings capture, but for a structured knowledge base with clear terminology, keyword matching works well.
- **FastAPI over Django** -- lightweight async API layer with auto-generated OpenAPI docs. No ORM overhead since SQLite queries are simple enough to write directly. Trade-off: no admin panel, but the dashboard covers that need.
- **Keyword sentiment over transformer models** -- deterministic, fast, zero GPU requirement. Trade-off: less accurate on nuanced text, but sufficient for routing and trend detection.

## Results & Metrics

- 24 API endpoints across 8 resource categories
- 8 database tables with foreign key enforcement
- 49 tests covering chatbot, copilot, customers, tickets, sentiment, and analytics
- Knowledge base seeded with 15 articles across 5 categories
- Health scoring refreshes on demand with sub-second response time

## Live Demo

[HuggingFace Space](https://huggingface.co/spaces/dbhavery/herald-customer-ops)

## Quick Start

```bash
git clone https://github.com/dbhavery/herald.git
cd herald
pip install -e ".[dev]"

# Run the server (auto-seeds demo data on first start)
uvicorn herald.main:app --reload --port 8091
```

No environment variables required for basic operation. If Ollama is running locally with `qwen3:8b`, the chatbot and copilot use it for generation; otherwise they fall back to knowledge-base-constructed and template responses.

## Lessons Learned

- **Sentiment calibration is domain-specific.** Generic keyword lists score "I need this fixed ASAP" as negative when it is just urgent. Had to separate urgency signals from dissatisfaction signals and weight them differently for the health score.
- **Citation-backed responses need careful prompt engineering.** The retrieval-to-generation-to-attribution pipeline can hallucinate citations if the prompt does not explicitly constrain the model to only reference retrieved content. Ended up using a structured prompt that lists sources by ID and instructs the model to cite by reference.
- **Health scoring is only useful with actionable thresholds.** A raw 0-100 number means nothing to a support team. Mapping scores to named risk tiers (low/medium/high) with specific recommended actions made the feature actually usable.

## Tests

49 tests across 6 modules. Each test runs against a fresh in-memory SQLite database seeded with demo data.

```bash
pytest tests/ -v
```
