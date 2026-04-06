from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from sentinel.clients.openfda import OpenFDAClient
from sentinel.config import settings
from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState, StatisticalSignal
from sentinel.stats.disproportionality import compute_ebgm, compute_prr, compute_ror
from sentinel.stats.trend import compute_trend


def _signal_strength(estimate: float, p_value: float, case_count: int) -> str:
    cfg = settings.signal_detection
    if case_count < cfg.min_case_count:
        return "none"
    if estimate >= max(cfg.prr_threshold * 1.5, 3.0) and p_value < 0.01:
        return "strong"
    if estimate >= cfg.prr_threshold and p_value < cfg.chi_square_alpha:
        return "moderate"
    if estimate > 1.2:
        return "weak"
    return "none"


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
    top_events: list[list[str | int]] = []
    execution_summary: dict[str, Any] = {}
    if summary_file.exists():
        execution_summary = json.loads(summary_file.read_text())
        top_events = execution_summary.get("top_events", [])
    if not top_events:
        top_events = event_profile.get("top_events", [])

    case_count = int(top_events[0][1]) if top_events else min(event_count, 10)
    non_case_count = max(event_count - case_count, 1)
    comparator_total = max(sum(count for _, count in top_events[1:6]), case_count + 20)
    comparator_case_count = max(int(comparator_total * 0.2), 1)
    comparator_non_case = max(comparator_total - comparator_case_count, 1)
    prr = compute_prr(case_count, non_case_count, comparator_case_count, comparator_non_case)
    ror = compute_ror(case_count, non_case_count, comparator_case_count, comparator_non_case)
    ebgm = compute_ebgm(case_count, expected=max(comparator_case_count, 1.0))
    trend_values = [_safe_int(value) for _, value in (execution_summary.get("timeline") or event_profile.get("timeline", []))]
    trend = compute_trend(trend_values[-8:] if trend_values else [case_count])
    event_term = str(top_events[0][0]) if top_events else "serious adverse events"
    known_in_label = event_term.lower() in known_terms_text if known_terms_text else False

    signals: list[StatisticalSignal] = [
        StatisticalSignal(
            event_term=event_term,
            method="prr",
            estimate=prr["estimate"],
            lower_ci=prr["lower_ci"],
            upper_ci=prr["upper_ci"],
            p_value=prr["p_value"],
            case_count=case_count,
            signal_strength=_signal_strength(prr["estimate"], prr["p_value"], case_count),
            known_in_label=known_in_label,
        ),
        StatisticalSignal(
            event_term=event_term,
            method="ror",
            estimate=ror["estimate"],
            lower_ci=ror["lower_ci"],
            upper_ci=ror["upper_ci"],
            p_value=ror["p_value"],
            case_count=case_count,
            signal_strength=_signal_strength(ror["estimate"], ror["p_value"], case_count),
            known_in_label=known_in_label,
        ),
        StatisticalSignal(
            event_term=event_term,
            method="ebgm",
            estimate=ebgm["estimate"],
            lower_ci=ebgm["lower_ci"],
            upper_ci=ebgm["upper_ci"],
            p_value=0.0,
            case_count=case_count,
            signal_strength="moderate" if ebgm["estimate"] >= settings.signal_detection.ebgm_threshold else "weak",
            known_in_label=known_in_label,
        ),
    ]
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
        "known_vs_new_signal": "known" if known_in_label else "potential_new",
    }
    add_progress(state, "analyze", "completed", f"Computed {len(signals)} signal estimates.")
    return state
