from __future__ import annotations

import json
from pathlib import Path

from sentinel.export_pdf import export_pdf
from sentinel.nodes.common import add_progress, now_iso
from sentinel.state import InvestigationState, ReviewRecord


def _export_outputs(state: InvestigationState, *, include_pdf: bool) -> list[str]:
    output_dir = Path.cwd() / ".sentinel_outputs" / state["investigation_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / "report.md"
    markdown_path.write_text(state.get("final_markdown", ""))

    audit_path = output_dir / "audit_trail.json"
    audit_path.write_text(json.dumps(state.get("audit_trail", []), indent=2))

    report_json_path = output_dir / "report_sections.json"
    report_json_path.write_text(json.dumps(state.get("report_sections", []), indent=2))

    review_path = output_dir / "review_log.json"
    review_path.write_text(json.dumps(state.get("review_log", []), indent=2))

    paths = [str(markdown_path), str(audit_path), str(report_json_path), str(review_path)]
    if include_pdf:
        pdf_path = output_dir / "report.pdf"
        paths.append(str(export_pdf(state, pdf_path)))
    return paths


def _record_review(state: InvestigationState, decision: str, correction: str) -> None:
    signals = state.get("signals", [])
    leading = signals[0] if signals else {}
    record = ReviewRecord(
        decision=decision,  # type: ignore[arg-type]
        correction=correction,
        recorded_at=now_iso(),
        review_tier=state.get("review_tier", "required"),  # type: ignore[arg-type]
        event_term=str(leading.get("event_term", "")),
        known_in_label=bool(leading.get("known_in_label", False)),
        signal_strength=str(leading.get("signal_strength", "none")),
        used_for_model_training=False,
    )
    state.setdefault("review_log", []).append(record)


def run(state: InvestigationState) -> InvestigationState:
    decision = state.get("human_decision", "pending")
    correction = state.get("reviewer_feedback", "").strip()
    if decision == "accept":
        _record_review(state, "accept", correction)
        state["status"] = "completed"
        state["output_paths"] = _export_outputs(state, include_pdf=True)
        add_progress(state, "human_gate", "completed", "Reviewer accepted the packet. The correction was logged and was not used to train a model.")
    elif decision == "escalate":
        _record_review(state, "escalate", correction)
        state["status"] = "escalated"
        state["output_paths"] = _export_outputs(state, include_pdf=True)
        add_progress(state, "human_gate", "completed", "Reviewer escalated the packet. The correction was logged and was not used to train a model.")
    elif decision == "reject":
        _record_review(state, "reject", correction)
        state["status"] = "rejected"
        state["output_paths"] = _export_outputs(state, include_pdf=False)
        add_progress(state, "human_gate", "failed", "Reviewer rejected the packet. The correction was logged and was not used to train a model.")
    else:
        state["status"] = "awaiting_review"
        state["human_decision"] = "pending"
        add_progress(state, "human_gate", "started", "Awaiting a reviewer decision: accept, reject, or escalate.")
    return state
