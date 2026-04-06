from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Sentinel — Launcher", page_icon="S")

st.title("Launch Investigation")
st.markdown(
    "Use the **sidebar** on the main page to start a new investigation.\n\n"
    "Navigate to the main page using the sidebar navigation."
)

if st.button("Go to main page"):
    st.switch_page("app.py")
