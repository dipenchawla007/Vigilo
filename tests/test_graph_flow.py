from __future__ import annotations

import json
from pathlib import Path

from sentinel.clients.llm import LLMClient
from sentinel.clients.openfda import OpenFDAClient
from sentinel.graph import InvestigationGraph


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.status_code = 200
        self.text = "OK"

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        if url.endswith("/drug/label.json"):
            payload = {
                "results": [
                    {
                        "adverse_reactions": ["nausea", "vomiting"]
                    }
                ]
            }
        else:
            payload = json.loads(Path("tests/fixtures/sample_faers_response.json").read_text())
        return FakeResponse(payload)


def test_graph_runs_to_human_review(tmp_path: Path) -> None:
    graph = InvestigationGraph(
        client=OpenFDAClient(session=FakeSession()),
        llm=LLMClient(),
        workspace=tmp_path,
    )
    state = graph.initial_state("metformin", "drug", 5)

    result = graph.run(state)

    assert result["status"] == "awaiting_review"
    assert result["execution"]["success"] is True
    assert result["report_sections"]
    assert result["human_decision"] == "pending"

    resumed = graph.resume(state["investigation_id"], human_decision="approve", reviewer_feedback="approved")
    assert resumed["status"] == "completed"
    assert resumed["output_paths"]
