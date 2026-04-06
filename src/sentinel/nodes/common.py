from __future__ import annotations

from datetime import datetime

from sentinel.state import InvestigationState, ProgressEvent


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_progress(state: InvestigationState, node: str, status: str, message: str) -> None:
    progress = state.setdefault("progress", [])
    progress.append(ProgressEvent(node=node, status=status, message=message, timestamp=now_iso()))

