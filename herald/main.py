"""Herald — Customer Operations Stack. FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from herald import __version__
from herald.analytics import get_churn_analysis, get_overview, get_resolution_metrics, get_sentiment_trend
from herald.chatbot import get_conversation, list_conversations, process_message
from herald.copilot import accept_suggestion, generate_suggestions
from herald.customers import get_customer, list_customers, refresh_customer_health, update_customer
from herald.database import init_db
from herald.knowledge import add_knowledge_item, list_knowledge_items, search_knowledge
from herald.models import (
    AgentReply,
    ChatRequest,
    CopilotAcceptRequest,
    CopilotSuggestRequest,
    CustomerUpdate,
    KnowledgeCreate,
    KnowledgeSearchRequest,
    OnboardingStartRequest,
    OnboardingStepUpdate,
    TicketCreate,
    TicketUpdate,
)
from herald.onboarding import complete_step, get_customer_onboarding, list_flows, start_onboarding
from herald.seed import seed_all
from herald.sentiment import analyze_sentiment
from herald.tickets import create_ticket, get_ticket, list_tickets, update_ticket

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("herald")

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("Herald v%s starting up", __version__)
    init_db()
    seed_all()
    logger.info("Database initialized and seeded")
    yield
    logger.info("Herald shutting down")


app = FastAPI(
    title="Herald",
    description="Customer Operations Stack — AI chatbot, support copilot, sentiment analytics, churn prediction",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health ====================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


# ==================== Customer Chat ====================

@app.post("/api/chat")
def chat(req: ChatRequest):
    """Process a customer chat message."""
    try:
        result = process_message(req.customer_id, req.message)
        return result
    except Exception as exc:
        logger.error("Chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/conversations")
def conversations_list(
    status: str | None = Query(None),
    customer_id: str | None = Query(None),
):
    """List conversations with optional filters."""
    return list_conversations(status=status, customer_id=customer_id)


@app.get("/api/conversations/{conversation_id}")
def conversation_detail(conversation_id: str):
    """Get conversation with all messages."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# ==================== Support Copilot ====================

@app.post("/api/copilot/suggest")
def copilot_suggest(req: CopilotSuggestRequest):
    """Generate copilot suggestions for a conversation."""
    try:
        result = generate_suggestions(req.conversation_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Copilot error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/copilot/accept")
def copilot_accept(req: CopilotAcceptRequest):
    """Mark a copilot suggestion as used."""
    result = accept_suggestion(req.suggestion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


# ==================== Customers ====================

@app.get("/api/customers")
def customers_list(
    plan: str | None = Query(None),
    churn_risk: str | None = Query(None),
):
    """List customers with optional filters."""
    return list_customers(plan=plan, churn_risk=churn_risk)


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str):
    """Get customer with stats."""
    cust = get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust


@app.patch("/api/customers/{customer_id}")
def customer_update(customer_id: str, updates: CustomerUpdate):
    """Update customer fields."""
    result = update_customer(customer_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


# ==================== Tickets ====================

@app.get("/api/tickets")
def tickets_list(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    category: str | None = Query(None),
):
    """List tickets with optional filters."""
    return list_tickets(status=status, priority=priority, category=category)


@app.post("/api/tickets")
def ticket_create(req: TicketCreate):
    """Create a new ticket."""
    try:
        result = create_ticket(
            customer_id=req.customer_id,
            subject=req.subject,
            description=req.description,
        )
        return result
    except Exception as exc:
        logger.error("Ticket creation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/api/tickets/{ticket_id}")
def ticket_update(ticket_id: str, updates: TicketUpdate):
    """Update ticket fields."""
    result = update_ticket(ticket_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return result


# ==================== Onboarding ====================

@app.get("/api/onboarding/flows")
def onboarding_flows():
    """List onboarding flows."""
    return list_flows()


@app.post("/api/onboarding/start")
def onboarding_start(req: OnboardingStartRequest):
    """Start an onboarding flow for a customer."""
    try:
        result = start_onboarding(req.customer_id, req.flow_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.patch("/api/onboarding/{onboarding_id}/step")
def onboarding_step(onboarding_id: str, update: OnboardingStepUpdate):
    """Mark an onboarding step as completed."""
    result = complete_step(onboarding_id, update.step_index)
    if not result:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    return result


# ==================== Knowledge Base ====================

@app.get("/api/knowledge")
def knowledge_list(category: str | None = Query(None)):
    """List knowledge items."""
    return list_knowledge_items(category=category)


@app.post("/api/knowledge")
def knowledge_create(req: KnowledgeCreate):
    """Add a knowledge item."""
    result = add_knowledge_item(req.title, req.content, req.category)
    return result


@app.post("/api/knowledge/search")
def knowledge_search(req: KnowledgeSearchRequest):
    """Search knowledge base."""
    results = search_knowledge(req.query)
    return results


# ==================== Analytics ====================

@app.get("/api/analytics/overview")
def analytics_overview():
    """Get key metrics overview."""
    return get_overview()


@app.get("/api/analytics/sentiment")
def analytics_sentiment():
    """Get sentiment trend data."""
    return get_sentiment_trend()


@app.get("/api/analytics/churn")
def analytics_churn():
    """Get churn risk analysis."""
    return get_churn_analysis()


@app.get("/api/analytics/resolution")
def analytics_resolution():
    """Get resolution time metrics."""
    return get_resolution_metrics()


# ==================== Dashboard ====================

@app.get("/dashboard")
@app.get("/dashboard/")
def serve_dashboard():
    """Serve the dashboard SPA."""
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(str(index), media_type="text/html")


# ==================== Main ====================

def main():
    """Run the Herald server."""
    uvicorn.run("herald.main:app", host="0.0.0.0", port=8091, reload=False)


if __name__ == "__main__":
    main()
