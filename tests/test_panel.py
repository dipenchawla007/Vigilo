from __future__ import annotations

from sentinel.nodes.panel import claim_problems, run
from sentinel.state import InvestigationState


def _signal(method: str, estimate: float, lower: float, upper: float, p_value: float) -> dict:
    return {
        "event_term": "NAUSEA",
        "method": method,
        "estimate": estimate,
        "lower_ci": lower,
        "upper_ci": upper,
        "p_value": p_value,
        "case_count": 40,
        "signal_strength": "moderate",
        "known_in_label": True,
        "citations": [
            {
                "cell": "a",
                "value": 40,
                "endpoint": "/drug/event.json",
                "query": "patient.drug.drugcharacterization:1",
                "full_url": "https://api.fda.gov/drug/event.json?search=a",
                "retrieved_at": "2026-11-02T00:00:00Z",
            },
            {
                "cell": "n_drug",
                "value": 200,
                "endpoint": "/drug/event.json",
                "query": "n_drug",
                "full_url": "https://api.fda.gov/drug/event.json?search=drug",
                "retrieved_at": "2026-11-02T00:00:00Z",
            },
            {
                "cell": "n_event",
                "value": 800,
                "endpoint": "/drug/event.json",
                "query": "n_event",
                "full_url": "https://api.fda.gov/drug/event.json?search=event",
                "retrieved_at": "2026-11-02T00:00:00Z",
            },
            {
                "cell": "n_total",
                "value": 10000,
                "endpoint": "/drug/event.json",
                "query": "n_total",
                "full_url": "https://api.fda.gov/drug/event.json?search=total",
                "retrieved_at": "2026-11-02T00:00:00Z",
            },
        ],
    }


def test_verifier_drops_a_number_that_was_not_computed() -> None:
    problems = claim_problems("PRR for NAUSEA is 999.00.", [], set(), role="statistician")
    assert problems


def test_panel_keeps_only_sourced_numbers() -> None:
    state = InvestigationState(
        product_name="metformin",
        progress=[],
        audit_trail=[
            {
                "endpoint": "/drug/label.json",
                "query": "label",
                "full_url": "https://api.fda.gov/drug/label.json?search=label",
                "record_count": 1,
                "retrieved_at": "2026-11-02T00:00:00Z",
                "context": "label",
                "raw_json_path": "",
            }
        ],
        signals=[
            _signal("prr", 2.58, 1.90, 3.50, 0.0123),
            _signal("ror", 2.70, 1.80, 4.10, 0.0200),
        ],
        analysis_summary={
            "contingency": {
                "event_term": "NAUSEA",
                "a": 40,
                "b": 160,
                "c": 760,
                "d": 9040,
                "n_drug": 200,
                "n_event": 800,
                "n_total": 10000,
                "expected": 16.0,
            }
        },
    )
    result = run(state)
    assert result["verification_issues"] == []
    assert any(claim["role"] == "statistician" and "2.58" in claim["text"] for claim in result["verified_claims"])
    assert any(claim["role"] == "challenger" for claim in result["verified_claims"])
    assert all(not any(char.isdigit() for char in claim["text"]) for claim in result["verified_claims"] if claim["role"] == "challenger")
