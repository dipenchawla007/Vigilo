"""Turn a contingency table into PRR, ROR, and EBGM signals."""

from __future__ import annotations

from typing import Any

from sentinel.config import settings
from sentinel.state import SourceRecord, StatisticalSignal
from sentinel.stats.contingency import ContingencyTable
from sentinel.stats.disproportionality import compute_ebgm, compute_prr, compute_ror, fit_hyperparameters


def _strength_from_ratio(estimate: float, p_value: float, case_count: int) -> str:
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


def _strength_from_ebgm(estimate: float, eb05: float, case_count: int) -> str:
    cfg = settings.signal_detection
    if case_count < cfg.min_case_count:
        return "none"
    if eb05 >= cfg.ebgm_threshold:
        return "strong"
    if estimate >= cfg.ebgm_threshold:
        return "moderate"
    if estimate > 1.2:
        return "weak"
    return "none"


def _signal(
    table: ContingencyTable,
    *,
    method: str,
    estimate: float,
    lower_ci: float,
    upper_ci: float,
    p_value: float,
    strength: str,
    known_in_label: bool,
    citations: list[dict[str, Any]],
) -> StatisticalSignal:
    return StatisticalSignal(
        event_term=table.event_term,
        method=method,
        estimate=estimate,
        lower_ci=lower_ci,
        upper_ci=upper_ci,
        p_value=p_value,
        case_count=table.a,
        signal_strength=strength,  # type: ignore[arg-type]
        known_in_label=known_in_label,
        citations=citations,
    )


def score_tables(
    tables: list[ContingencyTable],
    citations: dict[str, list[dict[str, Any]]],
    *,
    known_in_label: bool,
) -> dict[str, Any]:
    """Score the leading table and fit EBGM on every retrieved table."""
    if not tables:
        return {
            "signals": [],
            "contingency": {},
            "prior": {"status": "not_estimated", "theta": None, "pair_count": 0, "note": "No table was available."},
            "pairs": [],
        }
    leading = tables[0]
    leading_citations = citations.get(leading.event_term, [])
    prr = compute_prr(leading.a, leading.b, leading.c, leading.d)
    ror = compute_ror(leading.a, leading.b, leading.c, leading.d)
    signals = [
        _signal(
            leading,
            method="prr",
            estimate=prr["estimate"],
            lower_ci=prr["lower_ci"],
            upper_ci=prr["upper_ci"],
            p_value=prr["p_value"],
            strength=_strength_from_ratio(prr["estimate"], prr["p_value"], leading.a),
            known_in_label=known_in_label,
            citations=leading_citations,
        ),
        _signal(
            leading,
            method="ror",
            estimate=ror["estimate"],
            lower_ci=ror["lower_ci"],
            upper_ci=ror["upper_ci"],
            p_value=ror["p_value"],
            strength=_strength_from_ratio(ror["estimate"], ror["p_value"], leading.a),
            known_in_label=known_in_label,
            citations=leading_citations,
        ),
    ]
    pairs = [(table.a, table.expected) for table in tables]
    prior = fit_hyperparameters(pairs)
    theta = prior.get("theta")
    if theta:
        ebgm = compute_ebgm(leading.a, leading.expected, theta=tuple(theta))  # type: ignore[arg-type]
        signals.append(
            _signal(
                leading,
                method="ebgm",
                estimate=ebgm["estimate"],
                lower_ci=ebgm["lower_ci"],
                upper_ci=ebgm["upper_ci"],
                p_value=-1.0,
                strength=_strength_from_ebgm(ebgm["estimate"], ebgm["lower_ci"], leading.a),
                known_in_label=known_in_label,
                citations=leading_citations,
            )
        )
    return {
        "signals": signals,
        "contingency": leading.as_dict(),
        "prior": prior,
        "pairs": [{"event_term": table.event_term, "N": table.a, "E": table.expected} for table in tables],
    }


def known_in_label(event_term: str, label_text: str) -> bool:
    if not event_term or not label_text:
        return False
    return event_term.lower() in label_text


def margin_sources(citations: list[dict[str, Any]]) -> list[SourceRecord]:
    sources: list[SourceRecord] = []
    for citation in citations:
        sources.append(
            SourceRecord(
                endpoint=str(citation.get("endpoint", "")),
                query=str(citation.get("query", "")),
                full_url=str(citation.get("full_url", "")),
                record_count=int(citation.get("value", 0)),
                retrieved_at=str(citation.get("retrieved_at", "")),
                context=f"Count cell {citation.get('cell', '')}",
                raw_json_path="",
            )
        )
    return sources
