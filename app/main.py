from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents import SupportAgents
from app.config import get_settings
from app.contracts import ChatRequest, SupportTicket
from app.graph import SupportOrchestrator
from app.rag import KnowledgeBase


settings = get_settings()
kb = KnowledgeBase(settings.rag_docs_dir)
agents = SupportAgents(settings, kb)
orchestrator = SupportOrchestrator(agents)

app = FastAPI(title="Casearium Fintech Support Orchestrator", version="0.1.0")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": settings.default_text_model,
        "cloud_enabled": settings.cloud_enabled,
        "rag_documents": len(kb.documents),
    }


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    ticket = SupportTicket(
        message=request.message,
        client={"client_type_hint": request.client_type_hint, "company_id": request.company_id},
        attachments=request.attachments,
    )
    return orchestrator.invoke(ticket).model_dump(mode="json")


@app.get("/api/rag/search")
def rag_search(q: str, limit: int = 5) -> dict:
    return {"query": q, "hits": kb.search(q, limit=limit)}


@app.get("/api/analytics/demo")
def analytics_demo() -> dict:
    sample = [
        {"ticket_id": "t_1", "category": "access_issue", "justified": True},
        {"ticket_id": "t_2", "category": "payment_or_service_issue", "justified": True},
        {"ticket_id": "t_3", "category": "access_issue", "justified": False},
    ]
    return agents.analytics_report(sample)
