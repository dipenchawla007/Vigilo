from __future__ import annotations

from sentinel.clients.llm import LLMClient
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState


def run(state: InvestigationState, llm: LLMClient) -> InvestigationState:
    add_progress(state, "hypothesize", "started", f"Generating hypotheses for {state['product_name']}.")
    state["hypotheses"] = llm.generate_hypotheses(state["product_name"], state["product_type"])
    selected = next((h for h in state["hypotheses"] if h["status"] == "selected"), None)
    if selected:
        state["selected_hypothesis_id"] = selected["id"]
    else:
        state["hypotheses"][0]["status"] = "selected"
        state["selected_hypothesis_id"] = state["hypotheses"][0]["id"]
    add_progress(state, "hypothesize", "completed", f"Created {len(state['hypotheses'])} hypotheses. Selected: {state['selected_hypothesis_id']}.")
    return state
