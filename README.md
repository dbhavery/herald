# Herald — Customer Operations Stack

AI-powered customer operations: chatbot with knowledge search, support rep copilot, customer health scoring with churn prediction, ticket auto-categorization, sentiment analytics.

## Quick Start

```bash
pip install -e ".[dev]"
python -m herald.seed    # seed demo data
uvicorn herald.main:app --reload
```

## Tests

```bash
pytest tests/ -v
```

## API

- `POST /chat` — AI chatbot with knowledge search
- `POST /copilot/suggest` — Support rep copilot suggestions
- `GET /customers` — List customers with health scores
- `GET /tickets` — List support tickets
- `GET /analytics/overview` — Dashboard analytics
