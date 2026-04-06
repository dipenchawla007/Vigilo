from __future__ import annotations

import json
from pathlib import Path

from sentinel.export_pdf import export_pdf
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState


def _export_outputs(state: InvestigationState) -> list[str]:
    output_dir = Path.cwd() / ".sentinel_outputs" / state["investigation_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / "report.md"
    markdown_path.write_text(state.get("final_markdown", ""))

    audit_path = output_dir / "audit_trail.json"
    audit_path.write_text(json.dumps(state.get("audit_trail", []), indent=2))

    report_json_path = output_dir / "report_sections.json"
    report_json_path.write_text(json.dumps(state.get("report_sections", []), indent=2))

    pdf_path = output_dir / "report.pdf"
    actual_path = export_pdf(state, pdf_path)

    return [str(markdown_path), str(audit_path), str(report_json_path), str(actual_path)]


def run(state: InvestigationState) -> InvestigationState:
    decision = state.get("human_decision", "pending")
    if decision == "approve":
        state["status"] = "completed"
        state["output_paths"] = _export_outputs(state)
        add_progress(state, "human_gate", "completed", "Human review approved the report. PDF and artifacts exported.")
    elif decision == "request_changes":
        state["status"] = "revision_requested"
        add_progress(state, "human_gate", "retry", "Human review requested report changes.")
    elif decision == "reject":
        state["status"] = "rejected"
        add_progress(state, "human_gate", "failed", "Human review rejected the investigation.")
    else:
        state["status"] = "awaiting_review"
        state["human_decision"] = "pending"
        add_progress(state, "human_gate", "started", "Awaiting human review.")
    return state
