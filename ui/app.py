from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.export_pdf import export_pdf
from sentinel.graph import InvestigationGraph

st.set_page_config(page_title="Sentinel", page_icon="S", layout="wide")

if "investigation_state" not in st.session_state:
    st.session_state["investigation_state"] = None
if "investigation_running" not in st.session_state:
    st.session_state["investigation_running"] = False
if "trace_section" not in st.session_state:
    st.session_state["trace_section"] = None


def _run_in_background(graph: InvestigationGraph, state: dict) -> None:
    try:
        result = graph.run(state)
        st.session_state["investigation_state"] = result
    except Exception as exc:
        st.session_state["investigation_state"] = {
            **state,
            "status": "failed",
            "progress": state.get("progress", []) + [
                {"node": "system", "status": "failed", "message": f"Pipeline error: {exc}", "timestamp": ""}
            ],
        }
    finally:
        st.session_state["investigation_running"] = False


def start_investigation(product_name: str, product_type: str, time_range_years: int) -> None:
    graph = InvestigationGraph()
    state = graph.initial_state(
        product_name=product_name,
        product_type=product_type,
        time_range_years=time_range_years,
    )
    st.session_state["investigation_graph"] = graph
    st.session_state["investigation_id"] = state["investigation_id"]
    st.session_state["investigation_running"] = True
    st.session_state["trace_section"] = None

    thread = threading.Thread(target=_run_in_background, args=(graph, state), daemon=True)
    thread.start()
    st.session_state["investigation_state"] = state


# ── Sidebar: Investigation Launcher ──────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/shield.png", width=36)
    st.header("Sentinel")
    st.caption("Autonomous FDA Safety Intelligence")
    st.divider()

    product_name = st.text_input(
        "Enter a drug or device name to investigate",
        value=st.session_state.get("product_name", "metformin"),
        placeholder="e.g. metformin, lisinopril, insulin pump",
    )
    product_type = st.radio(
        "Product type",
        ["drug", "device"],
        index=0 if st.session_state.get("product_type", "drug") == "drug" else 1,
        horizontal=True,
    )
    time_range_years = st.slider("Time range (years)", min_value=1, max_value=10, value=5)

    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button(
            "Start investigation",
            type="primary",
            disabled=st.session_state.get("investigation_running", False),
            use_container_width=True,
        )
    with col2:
        if st.session_state.get("investigation_running"):
            st.button("Running...", disabled=True, use_container_width=True)

    if start_btn:
        st.session_state["product_name"] = product_name
        st.session_state["product_type"] = product_type
        start_investigation(product_name, product_type, time_range_years)
        st.rerun()

    st.divider()
    st.caption("Powered by openFDA public data")

    if st.session_state.get("investigation_running"):
        import time
        time.sleep(2)
        st.rerun()


# ── Main Area ────────────────────────────────────────────────────────────────

state = st.session_state.get("investigation_state")

if not state:
    st.title("Sentinel")
    st.subheader("Autonomous FDA Safety Intelligence Agent")
    st.markdown(
        "Type a drug or device name in the sidebar, and Sentinel will autonomously:\n"
        "1. Generate safety hypotheses\n"
        "2. Write and execute analysis code against live FDA data\n"
        "3. Compute signal detection statistics (PRR, ROR, EBGM, trend)\n"
        "4. Produce a traceable safety report\n"
        "5. Run compliance review\n"
        "6. Pause for your expert review before finalizing\n\n"
        "Every claim in the report links to the exact openFDA API call that produced the data."
    )
    st.stop()


# ── Status banner ────────────────────────────────────────────────────────────

status = state.get("status", "unknown")
status_map = {
    "running": ("Running investigation...", "🔄"),
    "awaiting_review": ("Awaiting your review", "⏸️"),
    "completed": ("Investigation completed", "✅"),
    "failed": ("Investigation failed", "❌"),
    "rejected": ("Investigation rejected", "🚫"),
    "revision_requested": ("Revision requested", "✏️"),
}
label, icon = status_map.get(status, (status, "ℹ️"))
st.title(f"{icon} {state.get('product_name', '')} — {label}")


# ── Tabs: Progress | Report | Review ────────────────────────────────────────

tab_progress, tab_report, tab_review = st.tabs(["Progress", "Report", "Review"])


# ── Tab 1: Live Progress Dashboard ──────────────────────────────────────────

with tab_progress:
    progress_events = state.get("progress", [])
    if not progress_events:
        st.info("Investigation starting...")
    else:
        node_order = ["hypothesize", "write_code", "execute", "analyze", "write_report", "review", "human_gate"]
        completed_nodes = {e["node"] for e in progress_events if e["status"] == "completed"}

        cols = st.columns(len(node_order))
        for i, node_name in enumerate(node_order):
            with cols[i]:
                if node_name in completed_nodes:
                    st.success(node_name.replace("_", " ").title(), icon="✅")
                elif any(e["node"] == node_name and e["status"] == "started" for e in progress_events):
                    st.warning(node_name.replace("_", " ").title(), icon="⏳")
                elif any(e["node"] == node_name and e["status"] in ("failed", "retry") for e in progress_events):
                    st.error(node_name.replace("_", " ").title(), icon="❌")
                else:
                    st.info(node_name.replace("_", " ").title(), icon="⬜")

        st.subheader("Event log")
        for event in reversed(progress_events):
            status_icon = {"started": "🔄", "completed": "✅", "retry": "🔁", "failed": "❌"}.get(event["status"], "ℹ️")
            st.markdown(f"`{event['timestamp']}` {status_icon} **{event['node']}** — {event['message']}")

    if state.get("compliance_issues"):
        st.subheader("Compliance review issues")
        for issue in state["compliance_issues"]:
            st.warning(issue, icon="⚠️")

    hypotheses = state.get("hypotheses", [])
    if hypotheses:
        st.subheader("Hypotheses")
        for h in hypotheses:
            status_icon = {"selected": "🎯", "pending": "⏳", "completed": "✅", "discarded": "⬜"}.get(h["status"], "ℹ️")
            st.markdown(f"{status_icon} **{h['title']}** ({h['method'].upper()}) — {h['rationale']}")

    artifacts = state.get("execution", {}).get("artifacts", [])
    if artifacts:
        st.subheader("Execution artifacts")
        for artifact in artifacts:
            kind_icon = {"plot": "📊", "json": "📄", "script": "🐍", "text": "📝"}.get(artifact["kind"], "📎")
            st.markdown(f"{kind_icon} `{artifact['filename']}`")
            if artifact["kind"] == "plot":
                p = Path(artifact["path"])
                if p.exists():
                    st.image(str(p), use_container_width=True)


# ── Tab 2: Report with Citation Trace Mode ──────────────────────────────────

with tab_report:
    sections = state.get("report_sections", [])
    signals = state.get("signals", [])

    if not sections:
        st.info("Report not yet generated. Investigation is in progress.")
    else:
        # Reading mode vs Trace mode toggle
        view_mode = st.radio("View mode", ["Reading", "Trace"], horizontal=True, key="report_view_mode")

        if view_mode == "Reading":
            for section in sections:
                with st.expander(section["heading"], expanded=True):
                    st.markdown(section["text"])

                    if section["heading"] == "Statistical analysis" and signals:
                        import pandas as pd
                        df = pd.DataFrame([
                            {
                                "Event": s["event_term"],
                                "Method": s["method"].upper(),
                                "Estimate": f"{s['estimate']:.2f}",
                                "95% CI": f"{s['lower_ci']:.2f} – {s['upper_ci']:.2f}",
                                "p-value": f"{s['p_value']:.4f}",
                                "Cases": s["case_count"],
                                "Strength": s["signal_strength"],
                                "In label": "Yes" if s.get("known_in_label") else "No",
                            }
                            for s in signals
                        ])
                        st.dataframe(df, use_container_width=True, hide_index=True)

                    if section.get("evidence_sentences"):
                        for ev in section["evidence_sentences"]:
                            source_count = len(ev.get("sources", []))
                            conf = f"{ev['confidence']:.0%}" if ev.get("confidence") else ""
                            st.caption(f"_{ev['text']}_ [{source_count} source(s), confidence: {conf}]")

        else:
            # Trace mode: side-by-side report text + source detail panel
            left_col, right_col = st.columns([3, 2])

            with left_col:
                for idx, section in enumerate(sections):
                    st.subheader(section["heading"])
                    st.markdown(section["text"])
                    if section.get("sources"):
                        if st.button(f"🔍 Trace sources ({len(section['sources'])})", key=f"trace_{idx}"):
                            st.session_state["trace_section"] = idx

            with right_col:
                st.subheader("Source trace panel")
                trace_idx = st.session_state.get("trace_section")
                if trace_idx is not None and trace_idx < len(sections):
                    section = sections[trace_idx]
                    st.markdown(f"**Section:** {section['heading']}")
                    st.divider()

                    for src in section.get("sources", []):
                        st.markdown(f"**Endpoint:** `{src.get('endpoint', '')}`")
                        st.code(src.get("full_url", ""), language="text")
                        st.caption(f"Retrieved: {src.get('retrieved_at', '')} | Records: {src.get('record_count', 0)}")

                        verify_url = src.get("full_url", "")
                        if verify_url:
                            st.markdown(f"[🔗 Verify in browser]({verify_url})")

                        if src.get("raw_json_path"):
                            raw_path = Path(src["raw_json_path"])
                            if raw_path.exists():
                                with st.expander("Raw JSON response"):
                                    try:
                                        st.json(json.loads(raw_path.read_text()))
                                    except json.JSONDecodeError:
                                        st.code(raw_path.read_text(), language="json")
                        st.divider()

                    for ev in section.get("evidence_sentences", []):
                        st.markdown(f"**Evidence:** _{ev['text']}_")
                        for s in ev.get("sources", []):
                            st.markdown(f"  ↳ `{s.get('endpoint', '')}` — [{s.get('record_count', 0)} records]({s.get('full_url', '')})")
                else:
                    st.info("Click a 'Trace sources' button on the left to inspect the data behind any section.")

    # Embedded plots
    artifacts = state.get("execution", {}).get("artifacts", [])
    plot_paths = [a for a in artifacts if a.get("kind") == "plot"]
    if plot_paths:
        st.subheader("Generated plots")
        for artifact in plot_paths:
            p = Path(artifact["path"])
            if p.exists():
                st.image(str(p), caption=artifact["filename"], use_container_width=True)


# ── Tab 3: Human Review Gate ────────────────────────────────────────────────

with tab_review:
    if status == "awaiting_review":
        st.subheader("Review decision")
        st.markdown(
            "The investigation pipeline has completed. Review the report in the **Report** tab, "
            "then make your decision below."
        )

        decision = st.radio(
            "Your decision",
            ["approve", "request_changes", "reject"],
            captions=[
                "Accept the report and generate final PDF output",
                "Send back to the report writer with feedback for revision",
                "Terminate this investigation (logged in audit trail)",
            ],
            key="review_decision",
        )
        feedback = st.text_area(
            "Reviewer feedback (optional for approve, required for request_changes)",
            value=state.get("reviewer_feedback", ""),
            key="reviewer_feedback_input",
        )

        if st.button("Submit review", type="primary"):
            graph = st.session_state.get("investigation_graph")
            investigation_id = st.session_state.get("investigation_id")
            if graph and investigation_id:
                result = graph.resume(
                    investigation_id,
                    human_decision=decision,
                    reviewer_feedback=feedback,
                )
                st.session_state["investigation_state"] = result
                st.rerun()
            else:
                st.error("Investigation graph not found in session. Please restart.")

    elif status == "completed":
        st.subheader("Investigation completed")
        st.success("The report has been approved and exported.")

        output_paths = state.get("output_paths", [])
        if output_paths:
            st.markdown("**Exported files:**")
            for p in output_paths:
                pp = Path(p)
                if pp.exists():
                    suffix = pp.suffix.lower()
                    if suffix == ".pdf":
                        with open(p, "rb") as f:
                            st.download_button(
                                f"Download {pp.name}",
                                data=f.read(),
                                file_name=pp.name,
                                mime="application/pdf",
                                type="primary",
                            )
                    elif suffix == ".html":
                        with open(p, "rb") as f:
                            st.download_button(
                                f"Download {pp.name}",
                                data=f.read(),
                                file_name=pp.name,
                                mime="text/html",
                                type="primary",
                            )
                    elif suffix == ".md":
                        with open(p, "r") as f:
                            st.download_button(
                                f"Download {pp.name}",
                                data=f.read(),
                                file_name=pp.name,
                                mime="text/markdown",
                            )
                    elif suffix == ".json":
                        with open(p, "r") as f:
                            st.download_button(
                                f"Download {pp.name}",
                                data=f.read(),
                                file_name=pp.name,
                                mime="application/json",
                            )
    elif status == "failed":
        st.error("Investigation failed. Check the Progress tab for details.")
    elif status == "rejected":
        st.warning("This investigation was rejected during review.")
    elif status == "running":
        st.info("Investigation is still running. Review will be available once all pipeline nodes complete.")
    else:
        st.info(f"Current status: {status}")
