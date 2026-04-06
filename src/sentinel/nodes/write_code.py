from __future__ import annotations

from sentinel.clients.llm import LLMClient
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState


def run(state: InvestigationState, llm: LLMClient) -> InvestigationState:
    hypothesis = next(h for h in state["hypotheses"] if h["id"] == state["selected_hypothesis_id"])
    add_progress(state, "write_code", "started", f"Writing analysis code for hypothesis: {hypothesis['title']}")

    error_feedback = ""
    execution = state.get("execution")
    if execution and not execution.get("success"):
        error_feedback = execution.get("stderr", "") or execution.get("stdout", "")

    state["generated_code"] = llm.write_code(
        {
            "product_name": state["product_name"],
            "product_type": state["product_type"],
            "hypothesis": hypothesis,
            "error_feedback": error_feedback,
        }
    )
    state["code_attempts"] = state.get("code_attempts", 0) + 1
    add_progress(state, "write_code", "completed", f"Generated investigation script (attempt {state['code_attempts']}).")
    return state
