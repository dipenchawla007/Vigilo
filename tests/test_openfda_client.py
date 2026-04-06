from __future__ import annotations

import json
from pathlib import Path

from sentinel.clients.openfda import OpenFDAClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = "OK") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls.append((url, params))
        return FakeResponse(self.payload)


def test_drug_events_builds_expected_query() -> None:
    payload = json.loads(Path("tests/fixtures/sample_faers_response.json").read_text())
    session = FakeSession(payload)
    client = OpenFDAClient(session=session)

    results, source = client.drug_events("metformin")

    assert len(results) == 2
    assert source["endpoint"] == "/drug/event.json"
    assert 'generic_name:"metformin"' in source["query"]
    assert session.calls[0][0].endswith("/drug/event.json")


def test_count_uses_meta_total() -> None:
    payload = json.loads(Path("tests/fixtures/sample_faers_response.json").read_text())
    session = FakeSession(payload)
    client = OpenFDAClient(session=session)

    count, _ = client.drug_event_count("metformin")

    assert count == 2

