from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from sentinel.clients.openfda import OpenFDAClient
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState
from sentinel.stats.faers_table import CASE_DEFINITION, retrieve_drug_tables
from sentinel.stats.openebgm_check import check_posterior
from sentinel.stats.signals import known_in_label, score_tables
from sentinel.stats.trend import compute_trend


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_drug_profile(events: list[dict[str, Any]]) -> dict[str, Any]:
    reaction_counts: Counter[str] = Counter()
    serious_outcomes: Counter[str] = Counter()
    reporter_types: Counter[str] = Counter()
    timeline: Counter[str] = Counter()
    for row in events:
        for reaction in row.get("patient", {}).get("reaction", []):
            term = reaction.get("reactionmeddrapt")
            if term:
                reaction_counts[str(term).upper()] += 1
        for flag in ["seriousnessdeath", "seriousnesshospitalization", "seriousnessdisabling", "seriousnesslifethreatening", "seriousnessother"]:
            if str(row.get(flag, "0")) in {"1", "True", "true"}:
                serious_outcomes[flag] += 1
        reporter = row.get("primarysource", {}).get("qualification") or "unknown"
        reporter_types[str(reporter)] += 1
        received = str(row.get("receivedate", ""))[:6]
        if received:
            timeline[received] += 1
    return {
        "top_events": reaction_counts.most_common(10),
        "serious_outcomes": dict(serious_outcomes),
        "reporter_types": dict(reporter_types),
        "timeline": sorted(timeline.items()),
    }


def _extract_device_profile(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_counts: Counter[str] = Counter()
    reporter_types: Counter[str] = Counter()
    timeline: Counter[str] = Counter()
    for row in events:
        term = row.get("event_type") or "UNKNOWN"
        event_counts[str(term).upper()] += 1
        reporter = row.get("report_source_code") or "unknown"
        reporter_types[str(reporter)] += 1
        received = str(row.get("date_received", ""))[:6]
        if received:
            timeline[received] += 1
    return {
        "top_events": event_counts.most_common(10),
        "serious_outcomes": dict(event_counts),
        "reporter_types": dict(reporter_types),
        "timeline": sorted(timeline.items()),
    }


def _flatten_label_text(records: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for record in records:
        for key in ["adverse_reactions", "warnings", "boxed_warning", "warnings_and_cautions"]:
            value = record.get(key, [])
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value:
                parts.append(str(value))
    return " ".join(parts).lower()


def run(state: InvestigationState, client: OpenFDAClient, workspace: Path) -> InvestigationState:
    add_progress(state, "analyze", "started", "Analyzing execution results and source data.")
    product_name = state["product_name"]
    sources = state.setdefault("audit_trail", [])
    is_drug = state["product_type"] == "drug"
    events, event_rows_source = client.drug_events(product_name, limit=300) if is_drug else client.device_events(product_name, limit=300)
    event_count, event_source = client.drug_event_count(product_name) if is_drug else client.count("/device/event.json", f'brand_name:"{product_name}"')
    sources.extend([event_source, event_rows_source])
    event_profile = _extract_drug_profile(events) if is_drug else _extract_device_profile(events)
    event_source["context"] = "Aggregate adverse event count"
    event_rows_source["context"] = "Detailed event rows used for summaries"

    label_results = []
    label_source = None
    recalls: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []
    recalls_source = None
    approvals_source = None
    device_clearances: list[dict[str, Any]] = []
    device_clearances_source = None
    if is_drug:
        label_results, label_source = client.drug_label(product_name)
        recalls, recalls_source = client.drug_recalls(product_name)
        approvals, approvals_source = client.drug_approvals(product_name)
        sources.append(label_source)
        sources.extend([recalls_source, approvals_source])
    else:
        recalls, recalls_source = client.device_recalls(product_name)
        device_clearances, device_clearances_source = client.device_510k(product_name)
        sources.extend([recalls_source, device_clearances_source])
    known_terms_text = _flatten_label_text(label_results)

    summary_file = workspace / "workspace" / "summary.json"
    execution_summary: dict[str, Any] = {}
    if summary_file.exists():
        execution_summary = json.loads(summary_file.read_text())

    trend_values = [_safe_int(value) for _, value in (execution_summary.get("timeline") or event_profile.get("timeline", []))]
    trend = compute_trend(trend_values[-8:] if trend_values else [0])
    scored: dict[str, Any] = {
        "signals": [],
        "contingency": {},
        "prior": {"status": "not_estimated", "theta": None, "pair_count": 0, "note": ""},
        "pairs": [],
    }
    openebgm_check: dict[str, Any] = {
        "status": "not_run",
        "detail": "Disproportionality counts are computed for drugs. Device runs do not build a FAERS table.",
    }
    count_status = "not_computed_for_devices"
    count_detail = "Device reports do not use the FAERS suspect-drug contingency table."
    if is_drug:
        count_result = retrieve_drug_tables(
            client,
            product_name,
            int(state.get("time_range_years", 5) or 5),
        )
        sources.extend(count_result.sources)
        count_status = count_result.status
        count_detail = count_result.detail
        labeled = False
        if count_result.tables:
            labeled = known_in_label(count_result.tables[0].event_term, known_terms_text)
            event_count = count_result.tables[0].n_drug
        scored = score_tables(count_result.tables, count_result.citations, known_in_label=labeled)
        pairs = [(int(item["N"]), float(item["E"])) for item in scored["pairs"]]
        openebgm_check = check_posterior(pairs, scored["prior"].get("theta"))
    signals = scored["signals"]
    contingency = scored["contingency"]
    labeled_event = bool(signals and signals[0]["known_in_label"])
    top_events = [[item["event_term"], item["N"]] for item in scored["pairs"]]
    if not top_events:
        top_events = event_profile.get("top_events", [])
    for source in sources:
        source["raw_json_path"] = ""
    analysis_dir = workspace / "workspace"
    if events:
        event_rows_source["raw_json_path"] = client.save_payload(analysis_dir / "event_rows.json", events[:25])
    if label_results and label_source:
        label_source["raw_json_path"] = client.save_payload(analysis_dir / "label_rows.json", label_results[:10])
    if recalls and recalls_source:
        recalls_source["raw_json_path"] = client.save_payload(analysis_dir / "recalls.json", recalls[:10])
    if approvals and approvals_source:
        approvals_source["raw_json_path"] = client.save_payload(analysis_dir / "approvals.json", approvals[:10])
    if device_clearances and device_clearances_source:
        device_clearances_source["raw_json_path"] = client.save_payload(analysis_dir / "device_clearances.json", device_clearances[:10])

    approval_date = ""
    if approvals:
        approval_date = str(approvals[0].get("original_approval_date", ""))
    if device_clearances:
        approval_date = str(device_clearances[0].get("decision_date", ""))

    state["data_profile"] = {
        "event_profile": event_profile,
        "label_records": len(label_results),
        "recall_count": len(recalls),
        "approval_count": len(approvals) or len(device_clearances),
        "approval_date": approval_date,
    }
    state["signals"] = signals
    state["analysis_summary"] = {
        "event_count": event_count,
        "top_events": top_events,
        "serious_outcomes": event_profile.get("serious_outcomes", {}),
        "reporter_types": event_profile.get("reporter_types", {}),
        "trend": trend,
        "recall_count": len(recalls),
        "approval_date": approval_date,
        "execution_summary": execution_summary,
        "known_vs_new_signal": "known" if labeled_event else "not_found_in_retrieved_label",
        "contingency": contingency,
        "case_definition": CASE_DEFINITION,
        "count_status": count_status,
        "count_detail": count_detail,
        "ebgm_prior": scored["prior"],
        "openebgm_check": openebgm_check,
        "count_pairs": scored["pairs"],
    }
    add_progress(state, "analyze", "completed", f"Computed {len(signals)} signal estimates.")
    return state
