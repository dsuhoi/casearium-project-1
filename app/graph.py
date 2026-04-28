from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents import SupportAgents
from app.contracts import AgentResult, OrchestratorResponse, SupportTicket


class SupportState(TypedDict, total=False):
    ticket: SupportTicket
    classifier: AgentResult
    files: AgentResult | None
    final: AgentResult
    rag_hits: list[dict[str, Any]]


class SupportOrchestrator:
    def __init__(self, agents: SupportAgents) -> None:
        self.agents = agents
        self.graph = self._build_graph()

    def invoke(self, ticket: SupportTicket) -> OrchestratorResponse:
        state = self.graph.invoke({"ticket": ticket})
        return OrchestratorResponse(
            ticket=ticket,
            classifier=state["classifier"],
            files=state.get("files"),
            final=state["final"],
            rag_hits=state.get("rag_hits", []),
        )

    def _build_graph(self):
        builder = StateGraph(SupportState)
        builder.add_node("classifier", self._classifier_node)
        builder.add_node("files", self._files_node)
        builder.add_node("domain", self._domain_node)
        builder.set_entry_point("classifier")
        builder.add_conditional_edges("classifier", self._after_classifier, {"files": "files", "domain": "domain"})
        builder.add_edge("files", "domain")
        builder.add_edge("domain", END)
        return builder.compile()

    def _classifier_node(self, state: SupportState) -> SupportState:
        state["classifier"] = self.agents.classifier(state["ticket"])
        return state

    def _files_node(self, state: SupportState) -> SupportState:
        state["files"] = self.agents.files(state["ticket"])
        return state

    @staticmethod
    def _after_classifier(state: SupportState) -> str:
        return "files" if state["ticket"].attachments else "domain"

    def _domain_node(self, state: SupportState) -> SupportState:
        ticket = state["ticket"]
        classifier_payload = state["classifier"].payload
        file_payload = state.get("files").payload if state.get("files") else None
        route_to = state["classifier"].route.next_agent
        if route_to == "security_ops_agent":
            final = self.agents.security_ops(ticket, file_payload)
        elif route_to == "b2b_expert_agent":
            final = self.agents.b2b_expert(ticket, classifier_payload)
        elif route_to == "complaints_agent":
            final = self.agents.complaints(ticket, classifier_payload, file_payload)
        elif route_to == "human_agent":
            final = self.agents._needs_human(ticket, "router", "human_requested")
        else:
            final = self.agents.b2c_consultant(ticket, classifier_payload, file_payload)
        state["final"] = final
        state["rag_hits"] = self.agents.kb.search(ticket.message, limit=3)
        return state
