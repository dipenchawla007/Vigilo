from __future__ import annotations

from sentinel.clients.llm import LLMClient
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState


def run(state: InvestigationState, llm: LLMClient) -> InvestigationState:
    add_progress(state, "review", "started", "Running compliance review.")
    issues = llm.review_report(
        {
            "report_sections": state.get("report_sections", []),
            "signals": state.get("signals", []),
            "analysis_summary": state.get("analysis_summary", {}),
        }
    )
    if state.get("analysis_summary", {}).get("event_count", 0) == 0:
        issues.append("No adverse event rows were retrieved; findings should be interpreted as an empty-data run.")
    state["review_attempts"] = state.get("review_attempts", 0) + 1
    state["compliance_issues"] = issues
    add_progress(
        state,
        "review",
        "completed" if not issues else "retry",
        "Compliance review passed." if not issues else f"Compliance review found {len(issues)} issues.",
    )
    return state
