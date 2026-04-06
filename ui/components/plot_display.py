from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_plot(path: str, caption: str = "") -> None:
    """Render a plot image if the file exists."""
    plot_path = Path(path)
    if plot_path.exists():
        st.image(str(plot_path), caption=caption or plot_path.name, use_container_width=True)
    else:
        st.info(f"Plot not available: {plot_path.name}")
