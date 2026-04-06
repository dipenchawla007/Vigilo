from __future__ import annotations

from typing import Iterable

import streamlit as st


def render_progress_feed(events: Iterable[dict[str, str]]) -> None:
    """Render a timestamped progress feed with status icons."""
    for event in events:
        icon = {
            "started": "🔄",
            "completed": "✅",
            "retry": "🔁",
            "failed": "❌",
        }.get(event.get("status", ""), "ℹ️")
        st.markdown(
            f"`{event.get('timestamp', '')}` {icon} "
            f"**{event.get('node', '')}** — {event.get('message', '')}"
        )
