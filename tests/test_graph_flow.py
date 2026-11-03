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

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeSession:
    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        if url.endswith("/drug/label.json"):
            return FakeResponse({"results": [{"adverse_reactions": ["nausea", "vomiting"]}]})
        if "count" in params:
            return FakeResponse(
                {
                    "results": [
                        {"term": "NAUSEA", "count": 40},
                        {"term": "VOMITING", "count": 30},
                        {"term": "HEADACHE", "count": 20},
                        {"term": "DIZZINESS", "count": 15},
                        {"term": "FATIGUE", "count": 12},
                    ]
                }
            )
        search = params.get("search", "")
        if params.get("limit") == 1:
            if "reactionmeddrapt" in search and "generic_name" in search:
                total = 40
            elif "reactionmeddrapt" in search:
                total = 800
            elif "drugcharacterization" in search:
                total = 200
            elif "receivedate" in search:
                total = 10000
            else:
                return FakeResponse(json.loads(Path("tests/fixtures/sample_faers_response.json").read_text()))
            return FakeResponse({"meta": {"results": {"total": total}}, "results": []})
        return FakeResponse(json.loads(Path("tests/fixtures/sample_faers_response.json").read_text()))


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
    assert "does not diagnose a patient" in result["final_markdown"]
    assert result["analysis_summary"]["contingency"]["a"] == 40
    assert result["analysis_summary"]["contingency"]["d"] == 9040
    assert result["verification_issues"] == []
    assert result["verified_claims"]
    assert any("drugcharacterization:1" in source["query"] for source in result["audit_trail"])

    blocked = graph.resume(state["investigation_id"], human_decision="escalate", reviewer_feedback="  ")
    assert blocked["status"] == "awaiting_review"
    assert "correction is required" in blocked["review_error"].lower()

    resumed = graph.resume(state["investigation_id"], human_decision="accept", reviewer_feedback="counts match the label")
    assert resumed["status"] == "completed"
    assert resumed["output_paths"]
    assert resumed["review_log"][0]["decision"] == "accept"
    assert resumed["review_log"][0]["used_for_model_training"] is False
    assert resumed["review_log"][0]["correction"] == "counts match the label"
