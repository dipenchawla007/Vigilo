from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from sentinel.clients.llm import LLMClient
from sentinel.clients.openfda import OpenFDAClient
from sentinel.config import settings
from sentinel.nodes import analyze, execute, human_gate, hypothesize, review, write_code, write_report
from sentinel.state import InvestigationState


class InvestigationGraph:
    def __init__(self, *, client: OpenFDAClient | None = None, llm: LLMClient | None = None, workspace: Path | None = None) -> None:
        self.client = client or OpenFDAClient()
        self.llm = llm or LLMClient(model=settings.llm_model)
        self.workspace = workspace or Path.cwd() / ".sentinel_runs"
        self.checkpointer = MemorySaver()
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(InvestigationState)

        def hypothesize_node(state: InvestigationState) -> InvestigationState:
            return hypothesize.run(state, self.llm)

        def write_code_node(state: InvestigationState) -> InvestigationState:
            return write_code.run(state, self.llm)

        def execute_node(state: InvestigationState) -> InvestigationState:
            run_dir = self.workspace / state["investigation_id"]
            return execute.run(state, run_dir)

        def analyze_node(state: InvestigationState) -> InvestigationState:
            run_dir = self.workspace / state["investigation_id"]
            return analyze.run(state, self.client, run_dir)

        def write_report_node(state: InvestigationState) -> InvestigationState:
            return write_report.run(state)

        def review_node(state: InvestigationState) -> InvestigationState:
            return review.run(state, self.llm)

        def human_gate_node(state: InvestigationState) -> InvestigationState:
            return human_gate.run(state)

        workflow.add_node("hypothesize", hypothesize_node)
        workflow.add_node("write_code", write_code_node)
        workflow.add_node("execute", execute_node)
        workflow.add_node("analyze", analyze_node)
        workflow.add_node("write_report", write_report_node)
        workflow.add_node("review", review_node)
        workflow.add_node("human_gate", human_gate_node)

        workflow.add_edge(START, "hypothesize")
        workflow.add_edge("hypothesize", "write_code")
        workflow.add_edge("write_code", "execute")
        workflow.add_conditional_edges(
            "execute",
            self._route_after_execute,
            {
                "retry_code": "write_code",
                "analyze": "analyze",
                "end_failed": END,
            },
        )
        workflow.add_edge("analyze", "write_report")
        workflow.add_edge("write_report", "review")
        workflow.add_conditional_edges(
            "review",
            self._route_after_review,
            {
                "rewrite_report": "write_report",
                "human_gate": "human_gate",
            },
        )
        workflow.add_conditional_edges(
            "human_gate",
            self._route_after_human_gate,
            {
                "rewrite_report": "write_report",
                "end": END,
            },
        )

        return workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_gate"],
            name="sentinel_investigation",
        )

    @staticmethod
    def _route_after_execute(state: InvestigationState) -> str:
        if state.get("execution", {}).get("success"):
            return "analyze"
        if state.get("code_attempts", 0) < settings.agent.max_code_retries:
            return "retry_code"
        state["status"] = "failed"
        return "end_failed"

    @staticmethod
    def _route_after_review(state: InvestigationState) -> str:
        if state.get("compliance_issues") and state.get("review_attempts", 0) <= settings.agent.max_review_retries:
            return "rewrite_report"
        return "human_gate"

    @staticmethod
    def _route_after_human_gate(state: InvestigationState) -> str:
        if state.get("human_decision") == "request_changes":
            return "rewrite_report"
        return "end"

    @staticmethod
    def build_config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    def initial_state(self, product_name: str, product_type: str = "drug", time_range_years: int = 5) -> InvestigationState:
        return InvestigationState(
            investigation_id=str(uuid.uuid4()),
            product_name=product_name,
            product_type=product_type,
            time_range_years=time_range_years,
            started_at=datetime.utcnow().isoformat() + "Z",
            status="running",
            code_attempts=0,
            review_attempts=0,
            progress=[],
            audit_trail=[],
        )

    def run(self, state: InvestigationState) -> InvestigationState:
        config = self.build_config(state["investigation_id"])
        result = self.app.invoke(state, config=config)
        snapshot = self.app.get_state(config)
        if snapshot.next == ("human_gate",):
            result["status"] = "awaiting_review"
            result["human_decision"] = "pending"
        elif result.get("execution", {}).get("success") is False:
            result["status"] = "failed"
        return result

    def resume(self, investigation_id: str, *, human_decision: str, reviewer_feedback: str = "") -> InvestigationState:
        config = self.build_config(investigation_id)
        result = self.app.invoke(
            Command(
                update={
                    "human_decision": human_decision,
                    "reviewer_feedback": reviewer_feedback,
                }
            ),
            config=config,
        )
        return result

    def get_state(self, investigation_id: str) -> InvestigationState:
        snapshot = self.app.get_state(self.build_config(investigation_id))
        return snapshot.values


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Sentinel investigation.")
    parser.add_argument("--product-name", "--drug", dest="product_name", required=True)
    parser.add_argument("--product-type", choices=["drug", "device"], default="drug")
    parser.add_argument("--time-range-years", type=int, default=5)
    args = parser.parse_args()

    graph = InvestigationGraph()
    state = graph.initial_state(args.product_name, args.product_type, args.time_range_years)
    result = graph.run(state)
    print(result.get("final_markdown", "No report generated."))


if __name__ == "__main__":
    main()
