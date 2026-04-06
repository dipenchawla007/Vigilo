from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import requests


API_BASE = "https://api.fda.gov"


@dataclass
class QueryResult:
    endpoint: str
    query: str
    full_url: str
    payload: dict[str, Any]
    record_count: int
    retrieved_at: str


def fetch_json(endpoint: str, search: str, limit: int = 100) -> QueryResult:
    url = f"{API_BASE}{endpoint}"
    response = requests.get(url, params={"search": search, "limit": limit}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    return QueryResult(
        endpoint=endpoint,
        query=search,
        full_url=response.url,
        payload=payload,
        record_count=len(results),
        retrieved_at=datetime.utcnow().isoformat() + "Z",
    )


def save_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2))


def save_plot(path: str, title: str, labels: list[str], values: list[int]) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path)

