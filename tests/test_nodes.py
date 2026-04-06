from __future__ import annotations

from sentinel.clients.llm import LLMClient
from sentinel.nodes.hypothesize import run as run_hypothesize
from sentinel.nodes.write_code import run as run_write_code
from sentinel.state import InvestigationState


def test_hypothesize_generates_multiple_hypotheses() -> None:
    state = InvestigationState(product_name="metformin", product_type="drug", progress=[])
    result = run_hypothesize(state, LLMClient())
    assert len(result["hypotheses"]) >= 3


def test_write_code_generates_python_script() -> None:
    state = InvestigationState(
        product_name="metformin",
        product_type="drug",
        progress=[],
        hypotheses=LLMClient().generate_hypotheses("metformin", "drug"),
        selected_hypothesis_id="h1",
        code_attempts=0,
    )
    result = run_write_code(state, LLMClient())
    assert "requests.get" in result["generated_code"]

