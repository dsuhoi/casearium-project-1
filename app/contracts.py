from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


AgentStatus = Literal["ok", "needs_human", "blocked", "error"]
ClientType = Literal["B2B", "B2C"]
Category = Literal["consultation", "complaint", "security_incident", "technical_issue", "escalation"]
Priority = Literal["Normal", "High", "Critical"]
RouteTo = Literal[
    "b2c_consultant_agent",
    "b2b_expert_agent",
    "security_ops_agent",
    "complaints_agent",
    "human_agent",
    "human_queue",
]


class ClientContext(BaseModel):
    client_id: str | None = None
    client_type_hint: ClientType | None = None
    company_id: str | None = None
    segment: str = "unknown"


class Attachment(BaseModel):
    attachment_id: str
    filename: str
    mime_type: str
    content_base64: str | None = None
    url: str | None = None


class SupportTicket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"t_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    message: str
    source: str = "web_chat"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client: ClientContext = Field(default_factory=ClientContext)
    attachments: list[Attachment] = Field(default_factory=list)
    dialog_history: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=lambda: {"channel": "chat", "locale": "ru-RU"})


class AgentRoute(BaseModel):
    next_agent: str
    reason: str


class AgentResult(BaseModel):
    ticket_id: str
    agent: str
    status: AgentStatus = "ok"
    route: AgentRoute
    payload: dict[str, Any] = Field(default_factory=dict)
    security_flags: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    observability: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str
    client_type_hint: ClientType | None = None
    company_id: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    ticket: SupportTicket
    classifier: AgentResult
    files: AgentResult | None = None
    final: AgentResult
    rag_hits: list[dict[str, Any]] = Field(default_factory=list)
