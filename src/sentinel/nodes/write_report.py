from __future__ import annotations

from sentinel.context_of_use import CONTEXT_OF_USE
from sentinel.nodes.common import add_progress
from sentinel.state import EvidenceSentence, InvestigationState, ReportSection, SourceRecord


def _sentence(text: str, sources: list[SourceRecord], confidence: float = 0.95) -> EvidenceSentence:
    return EvidenceSentence(text=text, sources=sources, confidence=confidence)


def _claims(state: InvestigationState, role: str) -> list[dict]:
    return [claim for claim in state.get("verified_claims", []) if claim["role"] == role]


def _join(claims: list[dict], fallback: str) -> str:
    if not claims:
        return fallback
    return " ".join(claim["text"] for claim in claims)


def run(state: InvestigationState) -> InvestigationState:
    add_progress(state, "write_report", "started", "Writing the evidence packet.")
    sources = state.get("audit_trail", [])
    analysis = state.get("analysis_summary", {})
    data_profile = state.get("data_profile", {})
    product_name = state["product_name"]
    approval_date = analysis.get("approval_date") or "not identified"
    product_sources = sources[:2] or sources
    check = analysis.get("openebgm_check", {})
    check_detail = str(check.get("detail") or "The external openEBGM check did not run.")
    prior_note = str((analysis.get("ebgm_prior") or {}).get("note") or "")
    methodology = (
        "Counts come from openFDA FAERS report totals. A report counts for the drug only when the "
        "search matches the drug name and the suspect role. The event is one preferred term, and the "
        "window is the received date. Cell a is suspect-drug reports that also contain the event. "
        "The other cells come from the drug total, the event total, and the count of every report in the window. "
        "PRR and ROR use those cells. EBGM is the geometric mean of the two-gamma posterior on the same counts. "
        f"{check_detail} {prior_note}"
    ).strip()
    statistician = _claims(state, "statistician")
    label = _claims(state, "label")
    challenger = _claims(state, "challenger")
    no_stats = "No verified disproportionality claims were available for this run."
    recommendation = (
        "A reviewer should accept, reject, or escalate this packet. "
        "The packet is a reporting pattern for a human reviewer. It is not a diagnosis, a causality decision, "
        "or a regulatory submission."
    )
    if state.get("review_tier") == "required":
        recommendation = (
            "This packet needs a reviewer because the event was not found in the retrieved label or a score "
            "was classified as strong. The reviewer accepts, rejects, or escalates it. "
            "The packet is not a diagnosis, a causality decision, or a regulatory submission."
        )

    sections: list[ReportSection] = [
        ReportSection(
            heading="Context of use",
            text=CONTEXT_OF_USE,
            sources=[],
            evidence_sentences=[_sentence(CONTEXT_OF_USE, [])],
            confidence=1.0,
        ),
        ReportSection(
            heading="Product identification",
            text=(
                f"{product_name} was screened as a {state['product_type']} product over a "
                f"{state['time_range_years']}-year received-date window. "
                f"The approval or clearance date found in the retrieved records is {approval_date}."
            ),
            sources=product_sources,
            evidence_sentences=[
                _sentence(f"{product_name} was screened as a {state['product_type']} product.", product_sources),
                _sentence(
                    f"The approval or clearance date found in the retrieved records is {approval_date}.",
                    product_sources,
                ),
            ],
            confidence=0.95,
        ),
        ReportSection(
            heading="Surveillance objective",
            text=(
                f"The screen asks whether public FAERS reporting for {product_name} is disproportionate "
                "for its leading preferred term. The result is a hypothesis for a reviewer."
            ),
            sources=product_sources,
            evidence_sentences=[
                _sentence(
                    f"The screen asks whether public FAERS reporting for {product_name} is disproportionate.",
                    product_sources,
                )
            ],
            confidence=0.92,
        ),
        ReportSection(
            heading="Data sources and methodology",
            text=methodology,
            sources=sources,
            evidence_sentences=[
                _sentence("PRR and ROR were computed from the openFDA contingency table.", sources),
                _sentence(check_detail, sources),
            ],
            confidence=0.91,
        ),
        ReportSection(
            heading="Adverse event summary",
            text=_join(
                statistician[:3],
                f"No suspect-drug contingency table was available. Sampled report rows: {analysis.get('event_count', 0)}.",
            ),
            sources=statistician[0]["sources"] if statistician else product_sources,
            evidence_sentences=[
                _sentence(claim["text"], claim["sources"]) for claim in statistician[:3]
            ] or [_sentence("No suspect-drug contingency table was available.", product_sources)],
            confidence=0.9,
        ),
        ReportSection(
            heading="Statistical analysis",
            text=_join(statistician[3:], no_stats),
            sources=statistician[0]["sources"] if statistician else product_sources,
            evidence_sentences=[
                _sentence(claim["text"], claim["sources"]) for claim in statistician[3:]
            ] or [_sentence(no_stats, product_sources)],
            confidence=0.88,
        ),
        ReportSection(
            heading="Signal assessment",
            text=_join(label + challenger, "No label or challenger claims were verified."),
            sources=(label[0]["sources"] if label and label[0]["sources"] else product_sources),
            evidence_sentences=[
                _sentence(claim["text"], claim["sources"] or product_sources) for claim in (label + challenger)
            ] or [_sentence("No label or challenger claims were verified.", product_sources)],
            confidence=0.86,
        ),
        ReportSection(
            heading="Limitations",
            text=(
                "FAERS is a passive surveillance system. Under-reporting, duplicate reporting, and "
                "stimulated reporting are expected. A disproportionality score is not a risk, a diagnosis, "
                "or a causality decision. This run does not stratify by age, sex, or year."
            ),
            sources=[],
            evidence_sentences=[],
            confidence=0.99,
        ),
        ReportSection(
            heading="Recommendations",
            text=recommendation,
            sources=product_sources,
            evidence_sentences=[_sentence(recommendation, product_sources)],
            confidence=0.84,
        ),
        ReportSection(
            heading="Audit trail appendix",
            text="Each source records the openFDA query, the retrieval time, and the count or rows that query returned.",
            sources=sources,
            evidence_sentences=[_sentence("The audit trail preserves the query URL and retrieval time.", sources)],
            confidence=0.98,
        ),
    ]
    state["report_sections"] = sections
    lines = ["# Vigilo safety evidence packet", "", CONTEXT_OF_USE, ""]
    for section in sections:
        if section["heading"] == "Context of use":
            continue
        lines.append(f"## {section['heading']}")
        lines.append(section["text"])
        if section["evidence_sentences"]:
            lines.append("")
            lines.append("Evidence:")
            for sentence in section["evidence_sentences"]:
                lines.append(f"- {sentence['text']}")
        if section["sources"]:
            lines.append("")
            lines.append("Sources:")
            for source in section["sources"]:
                raw_json = f" | raw_json={source['raw_json_path']}" if source.get("raw_json_path") else ""
                lines.append(f"- {source['full_url']} | retrieved_at={source['retrieved_at']}{raw_json}")
        lines.append("")
    if data_profile:
        lines.append("")
    state["final_markdown"] = "\n".join(lines).strip() + "\n"
    add_progress(state, "write_report", "completed", f"Drafted {len(sections)} report sections.")
    return state
