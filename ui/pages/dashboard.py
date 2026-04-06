from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Sentinel — Dashboard", page_icon="S")

st.title("Investigation Dashboard")

state = st.session_state.get("investigation_state")
if not state:
    st.info("No active investigation. Start one from the main page.")
    if st.button("Go to main page"):
        st.switch_page("app.py")
else:
    st.subheader(f"Product: {state.get('product_name', 'Unknown')}")
    st.caption(f"Type: {state.get('product_type', '')} | Status: {state.get('status', 'unknown')}")

    progress = state.get("progress", [])
    if progress:
        for event in reversed(progress):
            icon = {"started": "🔄", "completed": "✅", "retry": "🔁", "failed": "❌"}.get(event["status"], "ℹ️")
            st.markdown(f"`{event['timestamp']}` {icon} **{event['node']}** — {event['message']}")
    else:
        st.info("No progress events yet.")

    hypotheses = state.get("hypotheses", [])
    if hypotheses:
        st.subheader("Hypotheses")
        for h in hypotheses:
            status_icon = {"selected": "🎯", "pending": "⏳", "completed": "✅"}.get(h["status"], "ℹ️")
            st.markdown(f"{status_icon} **{h['title']}** ({h['method'].upper()})")
