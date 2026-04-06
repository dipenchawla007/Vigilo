from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import streamlit as st


def render_citation_viewer(sources: Iterable[dict[str, str]]) -> None:
    """Render a citation trace panel for a list of source records."""
    for source in sources:
        st.markdown(f"**Endpoint:** `{source.get('endpoint', 'unknown')}`")
        full_url = source.get("full_url", "")
        st.code(full_url, language="text")
        st.caption(
            f"Retrieved: {source.get('retrieved_at', 'N/A')} | "
            f"Records: {source.get('record_count', 0)}"
        )

        if full_url:
            st.markdown(f"[🔗 Verify in browser]({full_url})")

        raw_path_str = source.get("raw_json_path", "")
        if raw_path_str:
            raw_path = Path(raw_path_str)
            if raw_path.exists():
                with st.expander("Raw JSON response"):
                    try:
                        st.json(json.loads(raw_path.read_text()))
                    except (json.JSONDecodeError, OSError):
                        st.code(raw_path.read_text(), language="json")

        st.divider()
