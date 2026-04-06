"""PDF export for Sentinel safety investigation reports.

Converts the investigation state into an FDA-format PDF with embedded plots,
source citations, and a machine-readable audit trail appendix.
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from sentinel.state import InvestigationState


_CSS = """
@page {
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center { content: "Sentinel Safety Investigation — Page " counter(page) " of " counter(pages); font-size: 9px; color: #888; }
}
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}
h1 { font-size: 20pt; color: #0d3b66; border-bottom: 2px solid #0d3b66; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #14537a; margin-top: 24px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { font-size: 12pt; color: #333; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt; }
th { background: #0d3b66; color: white; padding: 8px 10px; text-align: left; }
td { padding: 6px 10px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background: #f7f9fb; }
.evidence { background: #eef6ff; border-left: 3px solid #0d3b66; padding: 8px 12px; margin: 8px 0; font-size: 10pt; }
.source-url { font-family: monospace; font-size: 9pt; color: #555; word-break: break-all; }
.signal-strong { color: #d32f2f; font-weight: bold; }
.signal-moderate { color: #f57c00; font-weight: bold; }
.signal-weak { color: #1976d2; }
.signal-none { color: #757575; }
.meta { font-size: 9pt; color: #888; }
.limitation { background: #fff8e1; border-left: 3px solid #ffa000; padding: 8px 12px; margin: 8px 0; }
img { max-width: 100%; height: auto; margin: 12px 0; }
.audit-entry { font-family: monospace; font-size: 8.5pt; padding: 4px 0; border-bottom: 1px dotted #ccc; }
"""


def _embed_image(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = base64.b64encode(p.read_bytes()).decode()
    suffix = p.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(suffix, "image/png")
    return f'<img src="data:{mime};base64,{data}" alt="{p.name}" />'


def _signal_class(strength: str) -> str:
    return f"signal-{strength}" if strength in ("strong", "moderate", "weak", "none") else "signal-none"


def _build_html(state: InvestigationState) -> str:
    sections = state.get("report_sections", [])
    signals = state.get("signals", [])
    audit_trail = state.get("audit_trail", [])
    product = state.get("product_name", "Unknown")
    product_type = state.get("product_type", "drug")

    parts: list[str] = [
        f"<html><head><style>{_CSS}</style></head><body>",
        f"<h1>Sentinel Safety Investigation: {product}</h1>",
        f'<p class="meta">Product type: {product_type} | '
        f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")} | '
        f'Investigation ID: {state.get("investigation_id", "N/A")}</p>',
    ]

    for section in sections:
        heading = section.get("heading", "")
        text = section.get("text", "")
        evidence = section.get("evidence_sentences", [])
        sources = section.get("sources", [])

        parts.append(f"<h2>{heading}</h2>")
        parts.append(f"<p>{text}</p>")

        if heading == "Statistical analysis" and signals:
            parts.append("<table><tr><th>Event term</th><th>Method</th><th>Estimate</th>"
                         "<th>95% CI</th><th>p-value</th><th>Cases</th><th>Strength</th><th>In label?</th></tr>")
            for sig in signals:
                cls = _signal_class(sig.get("signal_strength", "none"))
                parts.append(
                    f'<tr><td>{sig["event_term"]}</td><td>{sig["method"].upper()}</td>'
                    f'<td>{sig["estimate"]:.2f}</td>'
                    f'<td>{sig["lower_ci"]:.2f} – {sig["upper_ci"]:.2f}</td>'
                    f'<td>{sig["p_value"]:.4f}</td>'
                    f'<td>{sig["case_count"]}</td>'
                    f'<td class="{cls}">{sig["signal_strength"]}</td>'
                    f'<td>{"Yes" if sig.get("known_in_label") else "No"}</td></tr>'
                )
            parts.append("</table>")

        if heading == "Limitations":
            parts.append(f'<div class="limitation">{text}</div>')

        if evidence:
            for ev in evidence:
                parts.append(f'<div class="evidence">{ev["text"]}')
                for src in ev.get("sources", []):
                    parts.append(f'<br/><span class="source-url">{src.get("full_url", "")}</span>')
                parts.append("</div>")

        if sources and heading != "Audit trail appendix":
            parts.append("<details><summary>Sources</summary><ul>")
            for src in sources:
                parts.append(f'<li class="source-url">{src.get("full_url", "")} '
                             f'<span class="meta">(retrieved {src.get("retrieved_at", "")}; '
                             f'{src.get("record_count", 0)} records)</span></li>')
            parts.append("</ul></details>")

    # Embed plots
    artifacts = state.get("execution", {}).get("artifacts", [])
    plot_paths = [a["path"] for a in artifacts if a.get("kind") == "plot"]
    if plot_paths:
        parts.append("<h2>Generated plots</h2>")
        for pp in plot_paths:
            img = _embed_image(pp)
            if img:
                parts.append(img)

    # Audit trail appendix
    if audit_trail:
        parts.append("<h2>Audit trail (machine-readable)</h2>")
        for entry in audit_trail:
            parts.append(
                f'<div class="audit-entry">'
                f'<strong>{entry.get("endpoint", "")}</strong> | '
                f'{entry.get("full_url", "")} | '
                f'records: {entry.get("record_count", 0)} | '
                f'{entry.get("retrieved_at", "")}'
                f'</div>'
            )

    parts.append("</body></html>")
    return "\n".join(parts)


def export_pdf(state: InvestigationState, output_path: str | Path) -> Path:
    """Render the investigation report as a PDF file.

    Falls back to writing raw HTML if WeasyPrint is unavailable.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(state)

    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(output_path))
    except ImportError:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        return html_path

    return output_path
