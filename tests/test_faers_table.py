from __future__ import annotations

from datetime import date

from sentinel.clients.openfda import OpenFDAClient
from sentinel.stats.faers_table import retrieve_drug_tables, suspect_search


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.status_code = 200
        self.text = "OK"

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class CountingSession:
    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        search = params.get("search", "")
        if "count" in params:
            return FakeResponse(
                {
                    "results": [
                        {"term": "NAUSEA", "count": 40},
                        {"term": "VOMITING", "count": 30},
                        {"term": "HEADACHE", "count": 20},
                        {"term": "DIZZINESS", "count": 15},
                        {"term": "FATIGUE", "count": 12},
                    ]
                }
            )
        if "reactionmeddrapt" in search and "generic_name" in search:
            total = 40
        elif "reactionmeddrapt" in search:
            total = 800
        elif "drugcharacterization" in search:
            total = 200
        else:
            total = 10000
        return FakeResponse({"meta": {"results": {"total": total}}, "results": []})


def test_suspect_search_documents_role_and_window() -> None:
    query = suspect_search("metformin", 5, today=date(2026, 11, 2))
    assert 'openfda.generic_name:"metformin"' in query
    assert "patient.drug.drugcharacterization:1" in query
    assert "receivedate:[20211102+TO+20261102]" in query


def test_retrieve_builds_the_leading_table() -> None:
    client = OpenFDAClient(session=CountingSession())
    result = retrieve_drug_tables(client, "metformin", 5, today=date(2026, 11, 2))
    assert result.status == "ok"
    assert result.tables[0].event_term == "NAUSEA"
    assert result.tables[0].a == 40
    assert result.tables[0].n_drug == 200
    assert result.tables[0].n_total == 10000
    assert {citation["cell"] for citation in result.citations["NAUSEA"]} == {"a", "n_drug", "n_event", "n_total"}
