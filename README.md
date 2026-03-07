# Herald

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-49%20passing-brightgreen.svg)](#testing)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)

**Herald** is a customer operations platform that unifies AI-powered chat support, agent tooling, and predictive analytics into a single API. It gives support teams a chatbot that answers customer questions from a knowledge base, a copilot that suggests responses for human agents, and an analytics engine that scores customer health, predicts churn, and tracks sentiment over time.

---

## Features

- **AI Chatbot** -- Processes customer messages end-to-end: searches a TF-IDF knowledge base for context, builds a prompt with conversation history, generates responses via Ollama (with intelligent fallback), and auto-creates tickets when sentiment drops below threshold.
- **Agent Copilot** -- Generates three ranked response suggestions per conversation by combining knowledge base context with topic detection. Agents can accept suggestions with one click. Supports both LLM-generated and template-based suggestions.
- **Customer Health Scoring** -- Computes a 0-100 health score from four signals: recent activity, conversation sentiment, unresolved ticket count, and plan tier. Scores refresh on demand.
- **Churn Prediction** -- Maps health scores to risk tiers (low / medium / high) and surfaces at-risk customers with a breakdown dashboard.
- **Sentiment Analysis** -- Keyword-based scoring (-1.0 to +1.0) with exponential moving average per conversation. Powers auto-escalation and trend analytics.
- **Ticket Management** -- Full CRUD with auto-categorization (billing, bug, feature, technical) based on keyword analysis. Tickets link to conversations and track resolution times.
- **Knowledge Base** -- TF-IDF search with cosine similarity ranking and keyword boost. Feeds both the chatbot and copilot with relevant context.
- **Onboarding Flows** -- Step-by-step onboarding templates with per-customer progress tracking and completion state.
- **Analytics Dashboard** -- Overview metrics, daily sentiment trends, churn risk breakdown, and resolution time statistics (avg, p50, p95) with per-category drill-down.

---

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

The chatbot and copilot both query the knowledge base for context before generating responses. Sentiment scores feed back into conversation records, customer health calculations, and analytics aggregations. Ollama provides LLM generation when available; the system degrades gracefully with template-based fallbacks when it is not.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115+ with Pydantic v2 models |
| LLM | Ollama (qwen3:8b) with graceful fallback |
| Database | SQLite with WAL journaling and foreign keys |
| Search | TF-IDF vectorization with cosine similarity |
| Sentiment | Keyword-based scoring with EMA smoothing |
| HTTP Client | httpx (async-capable, used for Ollama calls) |
| Numerics | NumPy |
| Testing | pytest + pytest-asyncio |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/dbhavery/herald.git
cd herald
pip install -e ".[dev]"

# Run the server (auto-seeds demo data on first start)
uvicorn herald.main:app --reload --port 8091
```

The database initializes and seeds automatically on startup. No environment variables are required for basic operation. If Ollama is running locally on port 11434 with `qwen3:8b`, the chatbot and copilot will use it for generation; otherwise they fall back to knowledge-base-constructed and template responses.

**Optional:** To use LLM-powered responses, install and run [Ollama](https://ollama.ai):

```bash
ollama pull qwen3:8b
ollama serve
```

---

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check with version |

### Chatbot

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a customer message, get AI response with sentiment |
| `GET` | `/api/conversations` | List conversations (filter by `status`, `customer_id`) |
| `GET` | `/api/conversations/{id}` | Get conversation with full message history |

### Copilot

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/copilot/suggest` | Generate 3 response suggestions for a conversation |
| `POST` | `/api/copilot/accept` | Mark a suggestion as used by the agent |

### Customers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/customers` | List customers (filter by `plan`, `churn_risk`) |
| `GET` | `/api/customers/{id}` | Get customer with recent conversations and open tickets |
| `PATCH` | `/api/customers/{id}` | Update customer fields |

### Tickets

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tickets` | List tickets (filter by `status`, `priority`, `category`) |
| `POST` | `/api/tickets` | Create ticket with auto-categorization |
| `PATCH` | `/api/tickets/{id}` | Update ticket status, priority, assignment, resolution |

### Onboarding

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/onboarding/flows` | List active onboarding flows |
| `POST` | `/api/onboarding/start` | Start a flow for a customer |
| `PATCH` | `/api/onboarding/{id}/step` | Mark an onboarding step as completed |

### Knowledge Base

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/knowledge` | List knowledge items (filter by `category`) |
| `POST` | `/api/knowledge` | Add a knowledge item |
| `POST` | `/api/knowledge/search` | Search knowledge base by query |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/analytics/overview` | Key metrics: active conversations, avg sentiment, open tickets, at-risk customers |
| `GET` | `/api/analytics/sentiment` | Daily sentiment trend over last 30 days |
| `GET` | `/api/analytics/churn` | Churn risk breakdown with at-risk customer list |
| `GET` | `/api/analytics/resolution` | Ticket resolution time stats (avg, p50, p95) by category |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard` | Serves the single-page dashboard UI |

---

## Testing

```bash
pytest tests/ -v
```

49 tests across 6 test modules covering chatbot processing, copilot suggestions, customer CRUD and health scoring, ticket management and auto-categorization, sentiment analysis, and analytics aggregations. Each test runs against a fresh in-memory SQLite database seeded with demo data.

---

## Project Structure

```
herald/
├── herald/
│   ├── __init__.py          # Package version
│   ├── main.py              # FastAPI app, routes, lifespan
│   ├── models.py            # Pydantic request/response models
│   ├── database.py          # SQLite connection, schema, migrations
│   ├── chatbot.py           # AI chatbot: message processing, Ollama integration
│   ├── copilot.py           # Agent copilot: suggestion generation, topic detection
│   ├── customers.py         # Customer CRUD, health scoring, churn prediction
│   ├── tickets.py           # Ticket CRUD, auto-categorization
│   ├── sentiment.py         # Keyword-based sentiment analysis
│   ├── knowledge.py         # Knowledge base: TF-IDF search, cosine similarity
│   ├── onboarding.py        # Onboarding flow management, step tracking
│   ├── analytics.py         # Overview metrics, sentiment trends, churn analysis
│   └── seed.py              # Demo data seeder (8 customers, 12 conversations, 15 KB articles)
├── tests/
│   ├── conftest.py          # Shared fixtures (fresh DB per test)
│   ├── test_chatbot.py      # Chatbot processing tests
│   ├── test_copilot.py      # Copilot suggestion tests
│   ├── test_customers.py    # Customer management tests
│   ├── test_tickets.py      # Ticket management tests
│   ├── test_sentiment.py    # Sentiment scoring tests
│   └── test_analytics.py    # Analytics endpoint tests
├── dashboard/
│   └── index.html           # Single-page dashboard UI
├── pyproject.toml           # Project metadata and dependencies
├── LICENSE                  # MIT License
└── README.md
```

---

## License

MIT -- see [LICENSE](LICENSE) for details.
