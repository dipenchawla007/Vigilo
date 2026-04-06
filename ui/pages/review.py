from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Sentinel — Review", page_icon="S")

st.title("Report Review")

state = st.session_state.get("investigation_state")
if not state:
    st.info("No report available. Start an investigation from the main page.")
    if st.button("Go to main page"):
        st.switch_page("app.py")
    st.stop()

sections = state.get("report_sections", [])
if not sections:
    st.warning("Report has not been generated yet.")
    st.stop()

for section in sections:
    with st.expander(section["heading"], expanded=True):
        st.markdown(section["text"])

        if section.get("evidence_sentences"):
            st.caption("Evidence sentences:")
            for ev in section["evidence_sentences"]:
                st.markdown(f"- _{ev['text']}_")

        if section.get("sources"):
            st.caption("Sources:")
            for src in section["sources"]:
                st.code(src.get("full_url", ""), language="text")
                st.caption(f"Retrieved: {src.get('retrieved_at', '')} | Records: {src.get('record_count', 0)}")
                verify_url = src.get("full_url", "")
                if verify_url:
                    st.markdown(f"[Verify in browser]({verify_url})")

                if src.get("raw_json_path"):
                    raw_path = Path(src["raw_json_path"])
                    if raw_path.exists():
                        with st.expander("Raw JSON"):
                            try:
                                st.json(json.loads(raw_path.read_text()))
                            except json.JSONDecodeError:
                                st.code(raw_path.read_text(), language="json")
