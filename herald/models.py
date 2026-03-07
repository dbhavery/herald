"""Pydantic models for request/response validation."""

from typing import Optional

from pydantic import BaseModel, Field


# ---------- Chat ----------

class ChatRequest(BaseModel):
    customer_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sentiment: float


# ---------- Copilot ----------

class CopilotSuggestRequest(BaseModel):
    conversation_id: str


class CopilotSuggestResponse(BaseModel):
    suggestions: list[dict]
    context_used: list[str]


class CopilotAcceptRequest(BaseModel):
    suggestion_id: str


# ---------- Customers ----------

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    plan: Optional[str] = None
    health_score: Optional[float] = None
    churn_risk: Optional[str] = None
    last_active: Optional[str] = None


# ---------- Tickets ----------

class TicketCreate(BaseModel):
    customer_id: str
    subject: str
    description: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    category: Optional[str] = None


# ---------- Onboarding ----------

class OnboardingStartRequest(BaseModel):
    customer_id: str
    flow_id: str


class OnboardingStepUpdate(BaseModel):
    step_index: int


# ---------- Knowledge ----------

class KnowledgeCreate(BaseModel):
    title: str
    content: str
    category: str


class KnowledgeSearchRequest(BaseModel):
    query: str


# ---------- Agent message (for conversation reply) ----------

class AgentReply(BaseModel):
    conversation_id: str
    message: str
    agent_name: Optional[str] = "Support Agent"
