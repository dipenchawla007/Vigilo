from __future__ import annotations

from sentinel.nodes.common import add_progress
from sentinel.state import EvidenceSentence, InvestigationState, ReportSection, SourceRecord


def _sentence(text: str, sources: list[SourceRecord], confidence: float = 0.95) -> EvidenceSentence:
    return EvidenceSentence(text=text, sources=sources, confidence=confidence)


def run(state: InvestigationState) -> InvestigationState:
    add_progress(state, "write_report", "started", "Writing FDA-style report.")
    sources = state.get("audit_trail", [])
    analysis = state.get("analysis_summary", {})
    data_profile = state.get("data_profile", {})
    signals = state.get("signals", [])
    strongest = max(signals, key=lambda item: item["estimate"]) if signals else None
    product_name = state["product_name"]
    event_profile = data_profile.get("event_profile", {})
    top_events = analysis.get("top_events", [])
    top_event_list = ", ".join(f"{name} ({count})" for name, count in top_events[:5]) if top_events else "No major event terms identified."
    serious_summary = ", ".join(f"{key}={value}" for key, value in analysis.get("serious_outcomes", {}).items()) or "No serious outcome flags were present in the sampled records."
    reporter_summary = ", ".join(f"{key}={value}" for key, value in analysis.get("reporter_types", {}).items()) or "Reporter type distribution was unavailable."
    trend = analysis.get("trend", {})
    recall_count = analysis.get("recall_count", 0)
    approval_date = analysis.get("approval_date") or "not identified"
    signal_classification = analysis.get("known_vs_new_signal", "potential_new")
    recommendation = "No immediate escalation."
    if strongest and strongest["signal_strength"] in {"moderate", "strong"}:
        recommendation = "Escalate for safety scientist review and compare against label language and internal exposure data."
    elif strongest:
        recommendation = "Monitor in routine surveillance and confirm against broader evidence before action."

    product_sources = sources[:2]
    context_sources = sources[2:]

    sections: list[ReportSection] = [
        ReportSection(
            heading="Product identification",
            text=f"{product_name} was investigated as a {state['product_type']} product over a {state['time_range_years']}-year review window. The currently identified approval or clearance date is {approval_date}.",
            sources=product_sources,
            evidence_sentences=[
                _sentence(f"{product_name} was investigated as a {state['product_type']} product.", product_sources),
                _sentence(f"The currently identified approval or clearance date is {approval_date}.", context_sources or product_sources),
            ],
            confidence=0.95,
        ),
        ReportSection(
            heading="Surveillance objective",
            text=f"The investigation tested whether {product_name} shows a reportable safety signal using trend and disproportionality methods over public FDA surveillance data.",
            sources=product_sources,
            evidence_sentences=[_sentence(f"The investigation tested whether {product_name} shows a reportable safety signal.", product_sources)],
            confidence=0.92,
        ),
        ReportSection(
            heading="Data sources and methodology",
            text=(
                "Sentinel queried openFDA adverse event records, sampled detailed case rows, cross-referenced label or clearance context, "
                "and computed PRR, ROR, EBGM, plus time-trend metrics on the leading reported event term."
            ),
            sources=sources,
            evidence_sentences=[
                _sentence("Sentinel queried openFDA adverse event records and contextual regulatory sources.", sources),
                _sentence("PRR, ROR, EBGM, and trend metrics were computed on source-derived counts.", sources),
            ],
            confidence=0.91,
        ),
        ReportSection(
            heading="Adverse event summary",
            text=(
                f"The investigation identified {analysis.get('event_count', 0)} total reports for {product_name}. "
                f"Top reported event terms in the sampled records were: {top_event_list}. Serious outcome distribution: {serious_summary}. "
                f"Reporter distribution: {reporter_summary}."
            ),
            sources=product_sources,
            evidence_sentences=[
                _sentence(f"The investigation identified {analysis.get('event_count', 0)} total reports for {product_name}.", product_sources),
                _sentence(f"Top reported event terms were {top_event_list}.", product_sources),
            ],
            confidence=0.9,
        ),
        ReportSection(
            heading="Statistical analysis",
            text=(
                f"The strongest current estimate was {strongest['method'].upper()}={strongest['estimate']:.2f} "
                f"(95% CI {strongest['lower_ci']:.2f}-{strongest['upper_ci']:.2f}) for {strongest['event_term']}. "
                f"The reporting trend slope was {trend.get('slope', 0.0):.2f} with approximate p-value {trend.get('p_value', 1.0):.2f} "
                f"and period-over-period change {trend.get('yoy_change', 0.0):.2%}."
                if strongest
                else "No statistical estimates were available."
            ),
            sources=sources,
            evidence_sentences=[
                _sentence("Statistical signal estimates were computed from source-derived counts.", sources),
                _sentence(
                    f"The strongest estimate was {strongest['method'].upper()}={strongest['estimate']:.2f} for {strongest['event_term']}."
                    if strongest
                    else "No statistical estimates were available.",
                    sources,
                ),
            ],
            confidence=0.88,
        ),
        ReportSection(
            heading="Signal assessment",
            text=(
                f"The leading signal is classified as {strongest['signal_strength']} and is "
                f"{'already reflected in label language' if strongest and strongest['known_in_label'] else 'a potential label gap requiring review'}. "
                f"Current classification: {signal_classification}. Recall count identified during context review: {recall_count}."
                if strongest
                else "No actionable signal was detected."
            ),
            sources=sources,
            evidence_sentences=[
                _sentence("Signal assessment was compared against currently available label or regulatory context.", sources),
                _sentence(f"Recall count identified during context review was {recall_count}.", context_sources or sources),
            ],
            confidence=0.87,
        ),
        ReportSection(
            heading="Limitations",
            text="FAERS and MAUDE are passive surveillance systems subject to under-reporting, duplicate reporting, notoriety bias, and inability to establish causation.",
            sources=[],
            evidence_sentences=[],
            confidence=0.99,
        ),
        ReportSection(
            heading="Recommendations",
            text=recommendation,
            sources=sources,
            evidence_sentences=[_sentence(recommendation, sources)],
            confidence=0.84,
        ),
        ReportSection(
            heading="Audit trail appendix",
            text="Each source below contains the exact API URL, retrieval time, and optional local raw JSON artifact path captured during the investigation.",
            sources=sources,
            evidence_sentences=[_sentence("The audit trail preserves exact query URLs and retrieval metadata.", sources)],
            confidence=0.98,
        ),
    ]
    state["report_sections"] = sections
    lines = ["# Sentinel Safety Investigation", ""]
    for section in sections:
        lines.append(f"## {section['heading']}")
        lines.append(section["text"])
        if section["evidence_sentences"]:
            lines.append("")
            lines.append("Evidence sentences:")
            for sentence in section["evidence_sentences"]:
                lines.append(f"- {sentence['text']}")
        if section["sources"]:
            lines.append("")
            lines.append("Sources:")
            for source in section["sources"]:
                raw_json = f" | raw_json={source['raw_json_path']}" if source.get("raw_json_path") else ""
                lines.append(f"- {source['full_url']} | retrieved_at={source['retrieved_at']}{raw_json}")
        lines.append("")
    state["final_markdown"] = "\n".join(lines).strip() + "\n"
    add_progress(state, "write_report", "completed", f"Drafted {len(sections)} report sections.")
    return state
