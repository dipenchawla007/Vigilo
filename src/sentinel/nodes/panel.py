"""Evidence panel.

The statistician, label agent, and challenger may only phrase fields that were
already computed or retrieved. The verifier drops any sentence that introduces
a number those fields do not contain. None of these roles calls a model.
"""

from __future__ import annotations

import re

from sentinel.nodes.common import add_progress
from sentinel.state import InvestigationState, SourceRecord, VerifiedClaim
from sentinel.stats.signals import margin_sources


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _add_int(allowed: set[str], value: int) -> None:
    allowed.add(str(int(value)))


def _add_float(allowed: set[str], value: float) -> None:
    allowed.add(f"{float(value):.2f}")
    allowed.add(f"{float(value):.4f}")


def allowed_numbers(state: InvestigationState) -> set[str]:
    allowed: set[str] = set()
    analysis = state.get("analysis_summary", {})
    contingency = analysis.get("contingency") or {}
    for key in ("a", "b", "c", "d", "n_drug", "n_event", "n_total"):
        if key in contingency:
            _add_int(allowed, int(contingency[key]))
    if contingency.get("expected") is not None:
        _add_float(allowed, float(contingency["expected"]))
    for token in _NUMBER.findall(str(contingency.get("event_term", ""))):
        allowed.add(token)
    for signal in state.get("signals", []):
        _add_int(allowed, int(signal["case_count"]))
        _add_float(allowed, float(signal["estimate"]))
        _add_float(allowed, float(signal["lower_ci"]))
        _add_float(allowed, float(signal["upper_ci"]))
        if float(signal.get("p_value", -1)) >= 0:
            _add_float(allowed, float(signal["p_value"]))
        for token in _NUMBER.findall(str(signal.get("event_term", ""))):
            allowed.add(token)
        for citation in signal.get("citations", []):
            _add_int(allowed, int(citation["value"]))
    trend = analysis.get("trend") or {}
    for key in ("slope", "p_value", "yoy_change", "r_value"):
        if key in trend:
            _add_float(allowed, float(trend[key]))
    if state.get("time_range_years") is not None:
        _add_int(allowed, int(state["time_range_years"]))
    if analysis.get("event_count") is not None:
        _add_int(allowed, int(analysis["event_count"]))
    return allowed


def claim_problems(text: str, sources: list[SourceRecord], allowed: set[str], *, role: str) -> list[str]:
    numbers = _NUMBER.findall(text)
    problems: list[str] = []
    if role == "challenger" and numbers:
        problems.append("Challenger claim introduced a number.")
    for number in numbers:
        if number not in allowed:
            problems.append(f"Claim contains {number}, which is not a sourced field.")
    if numbers and not sources:
        problems.append("Quantitative claim has no source.")
    return problems


def _claim(
    role: str,
    text: str,
    sources: list[SourceRecord],
    citations: list[dict],
) -> VerifiedClaim:
    return VerifiedClaim(role=role, text=text, sources=sources, citations=citations)  # type: ignore[arg-type]


def _label_sources(state: InvestigationState) -> list[SourceRecord]:
    return [source for source in state.get("audit_trail", []) if source.get("endpoint") == "/drug/label.json"]


def statistician_claims(state: InvestigationState) -> list[VerifiedClaim]:
    contingency = state.get("analysis_summary", {}).get("contingency") or {}
    signals = state.get("signals", [])
    if not contingency or not signals:
        return []
    citations = list(signals[0].get("citations", []))
    sources = margin_sources(citations)
    term = str(contingency["event_term"])
    claims = [
        _claim(
            "statistician",
            f"Cell a for {term} is {int(contingency['a'])} suspect-drug reports that include this preferred term.",
            sources,
            citations,
        ),
        _claim(
            "statistician",
            f"Cell b for {term} is {int(contingency['b'])}. Cell c is {int(contingency['c'])}. Cell d is {int(contingency['d'])}.",
            sources,
            citations,
        ),
        _claim(
            "statistician",
            (
                f"The suspect-drug report total is {int(contingency['n_drug'])}. "
                f"Reports with this preferred term, for any drug, total {int(contingency['n_event'])}. "
                f"Reports in the window total {int(contingency['n_total'])}."
            ),
            sources,
            citations,
        ),
    ]
    for signal in signals:
        if signal["method"] == "ebgm":
            text = (
                f"EBGM for {term} is {signal['estimate']:.2f} "
                f"(posterior fifth percentile {signal['lower_ci']:.2f}, "
                f"posterior ninety-fifth percentile {signal['upper_ci']:.2f})."
            )
        else:
            text = (
                f"{signal['method'].upper()} for {term} is {signal['estimate']:.2f} "
                f"(interval {signal['lower_ci']:.2f} to {signal['upper_ci']:.2f}, "
                f"chi-square p-value {signal['p_value']:.4f})."
            )
        claims.append(_claim("statistician", text, sources, citations))
    return claims


def label_claims(state: InvestigationState) -> list[VerifiedClaim]:
    signals = state.get("signals", [])
    if not signals:
        return []
    term = str(signals[0]["event_term"])
    sources = _label_sources(state)
    if signals[0]["known_in_label"]:
        text = (
            f"The preferred term {term} appears in the retrieved label text. "
            "This is a text match against that label, not a causality decision."
        )
    else:
        text = (
            f"The preferred term {term} was not found in the retrieved label text. "
            "This is a text match against that label, not a determination that the event is new."
        )
    return [_claim("label", text, sources, [])]


def challenger_claims(state: InvestigationState) -> list[VerifiedClaim]:
    signals = state.get("signals", [])
    sources = margin_sources(signals[0].get("citations", [])) if signals else []
    statements = [
        "The reporting pattern is also consistent with the treated illness itself. This alternative was not tested against a background rate in this run.",
        "Stimulated reporting or duplicate reports can raise a count without a change in risk. This run did not deduplicate reports beyond the openFDA index.",
        "Age, sex, and year were not used as strata, so confounding by those factors remains possible.",
    ]
    return [_claim("challenger", text, sources, []) for text in statements]


def review_tier_for(state: InvestigationState) -> str:
    for signal in state.get("signals", []):
        if signal.get("signal_strength") == "strong" or not signal.get("known_in_label"):
            return "required"
    return "routine"


def run(state: InvestigationState) -> InvestigationState:
    add_progress(state, "evidence_panel", "started", "Checking statistician, label, and challenger claims against sourced fields.")
    allowed = allowed_numbers(state)
    verified: list[VerifiedClaim] = []
    issues: list[str] = []
    for claim in [*statistician_claims(state), *label_claims(state), *challenger_claims(state)]:
        problems = claim_problems(claim["text"], claim["sources"], allowed, role=claim["role"])
        if problems:
            issues.extend(f"{claim['role']}: {problem}" for problem in problems)
            continue
        verified.append(claim)
    state["verified_claims"] = verified
    state["verification_issues"] = issues
    state["review_tier"] = review_tier_for(state)  # type: ignore[typeddict-item]
    add_progress(
        state,
        "evidence_panel",
        "completed",
        f"Kept {len(verified)} sourced claims. Review tier is {state['review_tier']}.",
    )
    return state
