from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any

import requests

from sentinel.config import settings
from sentinel.state import SourceRecord

logger = logging.getLogger(__name__)


class OpenFDAError(RuntimeError):
    """Raised when the openFDA API returns an error."""


@dataclass
class OpenFDAClient:
    base_url: str = settings.openfda_base_url
    session: requests.Session | None = None
    max_retries: int = 3
    backoff_base: float = 1.0

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def _request(self, endpoint: str, *, search: str, limit: int = 100, skip: int = 0) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params={"search": search, "limit": limit, "skip": skip},
                    timeout=30,
                )
                if response.status_code == 429:
                    wait = self.backoff_base * (2 ** attempt)
                    logger.warning("openFDA rate limited (429). Retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, self.max_retries)
                    time.sleep(wait)
                    continue
                if response.status_code >= 500:
                    wait = self.backoff_base * (2 ** attempt)
                    logger.warning("openFDA server error (%d). Retrying in %.1fs (attempt %d/%d)", response.status_code, wait, attempt + 1, self.max_retries)
                    time.sleep(wait)
                    continue
                if response.status_code == 404:
                    return {"meta": {"results": {"total": 0}}, "results": []}
                if response.status_code >= 400:
                    raise OpenFDAError(f"openFDA request failed: {response.status_code} {response.text}")
                return response.json()
            except requests.ConnectionError as exc:
                last_exc = exc
                wait = self.backoff_base * (2 ** attempt)
                logger.warning("openFDA connection error. Retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, self.max_retries)
                time.sleep(wait)
            except requests.Timeout as exc:
                last_exc = exc
                wait = self.backoff_base * (2 ** attempt)
                logger.warning("openFDA timeout. Retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, self.max_retries)
                time.sleep(wait)
            except requests.RequestException:
                return {"meta": {"results": {"total": 0}}, "results": []}

        if last_exc:
            logger.error("openFDA request failed after %d retries: %s", self.max_retries, last_exc)
        return {"meta": {"results": {"total": 0}}, "results": []}

    def _source(self, endpoint: str, query: str, record_count: int) -> SourceRecord:
        return SourceRecord(
            endpoint=endpoint,
            query=query,
            full_url=f"{self.base_url}{endpoint}?search={query}",
            record_count=record_count,
            retrieved_at=datetime.utcnow().isoformat() + "Z",
            context="openFDA query result",
            raw_json_path="",
        )

    def search(self, endpoint: str, query: str, limit: int = 100) -> tuple[list[dict[str, Any]], SourceRecord]:
        payload = self._request(endpoint, search=query, limit=limit)
        results = payload.get("results", [])
        return results, self._source(endpoint, query, len(results))

    def paginated_search(self, endpoint: str, query: str, *, limit: int = 100, max_records: int = 500) -> tuple[list[dict[str, Any]], SourceRecord]:
        results: list[dict[str, Any]] = []
        skip = 0
        while skip < max_records:
            page = self._request(endpoint, search=query, limit=min(limit, max_records - skip), skip=skip)
            page_results = page.get("results", [])
            if not page_results:
                break
            results.extend(page_results)
            if len(page_results) < limit:
                break
            skip += limit
        return results, self._source(endpoint, query, len(results))

    def count(self, endpoint: str, query: str) -> tuple[int, SourceRecord]:
        payload = self._request(endpoint, search=query, limit=1)
        count = payload.get("meta", {}).get("results", {}).get("total", len(payload.get("results", [])))
        return int(count), self._source(endpoint, query, int(count))

    def count_by_field(self, endpoint: str, query: str, field: str, *, limit: int = 25) -> tuple[list[dict[str, Any]], SourceRecord]:
        url = f"{self.base_url}{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params={"search": query, "count": field, "limit": limit},
                    timeout=30,
                )
                if response.status_code == 429:
                    wait = self.backoff_base * (2 ** attempt)
                    time.sleep(wait)
                    continue
                if response.status_code >= 500:
                    wait = self.backoff_base * (2 ** attempt)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", [])
                return results, self._source(endpoint, f"{query} | count={field}", len(results))
            except requests.ConnectionError as exc:
                last_exc = exc
                time.sleep(self.backoff_base * (2 ** attempt))
            except requests.Timeout as exc:
                last_exc = exc
                time.sleep(self.backoff_base * (2 ** attempt))
            except requests.RequestException:
                break

        if last_exc:
            logger.error("openFDA count_by_field failed after retries: %s", last_exc)
        return [], self._source(endpoint, f"{query} | count={field}", 0)

    def save_payload(self, path: Path, payload: Any) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        return str(path)

    # -- Drug endpoints --

    def drug_events(self, product_name: str, limit: int = 100) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'patient.drug.openfda.generic_name:"{product_name}"'
        return self.paginated_search("/drug/event.json", query, limit=100, max_records=limit)

    def drug_event_count(self, product_name: str) -> tuple[int, SourceRecord]:
        query = f'patient.drug.openfda.generic_name:"{product_name}"'
        return self.count("/drug/event.json", query)

    def drug_label(self, product_name: str, limit: int = 5) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'openfda.generic_name:"{product_name}"'
        return self.search("/drug/label.json", query, limit=limit)

    def drug_recalls(self, product_name: str, limit: int = 20) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'product_description:"{product_name}"'
        return self.search("/drug/enforcement.json", query, limit=limit)

    def drug_approvals(self, product_name: str, limit: int = 10) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'products.brand_name:"{product_name}"+OR+products.generic_name:"{product_name}"'
        return self.search("/drug/drugsfda.json", query, limit=limit)

    # -- Device endpoints --

    def device_events(self, product_name: str, limit: int = 100) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'brand_name:"{product_name}"'
        return self.paginated_search("/device/event.json", query, limit=100, max_records=limit)

    def device_510k(self, product_name: str, limit: int = 20) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'device_name:"{product_name}"'
        return self.search("/device/510k.json", query, limit=limit)

    def device_recalls(self, product_name: str, limit: int = 20) -> tuple[list[dict[str, Any]], SourceRecord]:
        query = f'product_description:"{product_name}"'
        return self.search("/device/enforcement.json", query, limit=limit)
