"""Retrieve the openFDA counts that fill a drug-event contingency table."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sentinel.clients.openfda import OpenFDAClient
from sentinel.state import SourceRecord
from sentinel.stats.contingency import CASE_DEFINITION, ContingencyTable, build_contingency


DRUG_ENDPOINT = "/drug/event.json"


def _quote(value: str) -> str:
    return value.replace('"', "").strip()


def receivedate_clause(years: int, today: date | None = None) -> str:
    end = today or datetime.utcnow().date()
    try:
        start = end.replace(year=end.year - years)
    except ValueError:
        start = end.replace(year=end.year - years, day=28)
    return f"[{start.strftime('%Y%m%d')}+TO+{end.strftime('%Y%m%d')}]"


def suspect_search(
    product_name: str,
    years: int,
    *,
    drug_field: str = "openfda.generic_name",
    event_term: str | None = None,
    today: date | None = None,
) -> str:
    parts = [
        f'patient.drug.{drug_field}:"{_quote(product_name)}"',
        "patient.drug.drugcharacterization:1",
        f"receivedate:{receivedate_clause(years, today)}",
    ]
    if event_term:
        parts.append(f'patient.reaction.reactionmeddrapt.exact:"{_quote(event_term)}"')
    return "+AND+".join(parts)


def event_search(event_term: str, years: int, today: date | None = None) -> str:
    return (
        f'patient.reaction.reactionmeddrapt.exact:"{_quote(event_term)}"'
        f"+AND+receivedate:{receivedate_clause(years, today)}"
    )


def window_search(years: int, today: date | None = None) -> str:
    return f"receivedate:{receivedate_clause(years, today)}"


@dataclass
class DrugCountResult:
    tables: list[ContingencyTable] = field(default_factory=list)
    sources: list[SourceRecord] = field(default_factory=list)
    citations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    drug_field: str = "openfda.generic_name"
    case_definition: str = CASE_DEFINITION
    status: str = "ok"
    detail: str = ""


def _citation(cell: str, value: int, source: SourceRecord) -> dict[str, Any]:
    return {
        "cell": cell,
        "value": int(value),
        "endpoint": source["endpoint"],
        "query": source["query"],
        "full_url": source["full_url"],
        "retrieved_at": source["retrieved_at"],
    }


def retrieve_drug_tables(
    client: OpenFDAClient,
    product_name: str,
    years: int,
    *,
    today: date | None = None,
    event_limit: int = 5,
) -> DrugCountResult:
    """Build contingency tables for the most-reported suspect-drug events."""
    result = DrugCountResult()
    drug_field = "openfda.generic_name"
    drug_query = suspect_search(product_name, years, drug_field=drug_field, today=today)
    n_drug, drug_source = client.count(DRUG_ENDPOINT, drug_query)
    if n_drug <= 0:
        drug_field = "medicinalproduct"
        drug_query = suspect_search(product_name, years, drug_field=drug_field, today=today)
        n_drug, drug_source = client.count(DRUG_ENDPOINT, drug_query)
    result.drug_field = drug_field
    result.sources.append(drug_source)
    if n_drug <= 0:
        result.status = "no_reports"
        result.detail = "openFDA returned no suspect-drug reports for this product in the window."
        return result

    n_total, total_source = client.count(DRUG_ENDPOINT, window_search(years, today))
    result.sources.append(total_source)
    buckets, bucket_source = client.count_by_field(
        DRUG_ENDPOINT,
        drug_query,
        "patient.reaction.reactionmeddrapt.exact",
        limit=event_limit,
    )
    result.sources.append(bucket_source)
    terms = [(str(item["term"]), int(item["count"])) for item in buckets if item.get("term") and item.get("count")]
    if not terms:
        result.status = "no_events"
        result.detail = "openFDA returned suspect-drug reports but no preferred-term counts."
        return result

    for index, (term, bucket_count) in enumerate(terms):
        if index == 0:
            observed, observed_source = client.count(
                DRUG_ENDPOINT,
                suspect_search(product_name, years, drug_field=drug_field, event_term=term, today=today),
            )
            result.sources.append(observed_source)
            if observed <= 0:
                observed = bucket_count
                observed_source = bucket_source
        else:
            observed = bucket_count
            observed_source = bucket_source
        n_event, event_source = client.count(DRUG_ENDPOINT, event_search(term, years, today))
        result.sources.append(event_source)
        table = build_contingency(
            event_term=term,
            observed=observed,
            n_drug=n_drug,
            n_event=n_event,
            n_total=n_total,
        )
        if table is None:
            continue
        result.tables.append(table)
        result.citations[term] = [
            _citation("a", table.a, observed_source),
            _citation("n_drug", table.n_drug, drug_source),
            _citation("n_event", table.n_event, event_source),
            _citation("n_total", table.n_total, total_source),
        ]
    if not result.tables:
        result.status = "inconsistent_counts"
        result.detail = "The openFDA margins could not form a non-negative contingency table."
    return result
