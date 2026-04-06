from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import requests

from sentinel.config import settings
from sentinel.state import Hypothesis


@dataclass
class LLMClient:
    """LLM adapter supporting Anthropic Claude, OpenAI GPT-4o, Gemini, and a
    deterministic placeholder fallback.

    Provider resolution order (when ``provider="auto"``):
      1. anthropic  — if ANTHROPIC_API_KEY is set
      2. openai     — if OPENAI_API_KEY is set
      3. gemini     — if GEMINI_API_KEY is set
      4. placeholder
    """

    model: str = "deterministic-fallback"
    provider: str = "auto"

    def is_placeholder(self) -> bool:
        return self._resolved_provider() == "placeholder"

    def _resolved_provider(self) -> str:
        if self.provider != "auto":
            return self.provider
        if settings.anthropic_api_key:
            return "anthropic"
        if settings.openai_api_key:
            return "openai"
        if settings.gemini_api_key:
            return "gemini"
        return "placeholder"

    def _resolved_model(self) -> str:
        if self.model != "deterministic-fallback":
            return self.model
        provider = self._resolved_provider()
        return {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "gemini": "gemini-2.5-flash",
        }.get(provider, "deterministic-fallback")

    # ------------------------------------------------------------------
    # JSON extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(text: str) -> Any:
        text = text.strip()
        if not text:
            raise ValueError("Empty model response")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    @staticmethod
    def _extract_code(text: str) -> str:
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    # ------------------------------------------------------------------
    # Provider-specific generation
    # ------------------------------------------------------------------
    def _generate(self, *, system: str, prompt: str, temperature: float = 0.0, expect_json: bool = True) -> str:
        provider = self._resolved_provider()
        if provider == "anthropic":
            return self._anthropic_generate(system=system, prompt=prompt, temperature=temperature)
        if provider == "openai":
            return self._openai_generate(system=system, prompt=prompt, temperature=temperature, expect_json=expect_json)
        if provider == "gemini":
            return self._gemini_generate(system_instruction=system, prompt=prompt, temperature=temperature)
        raise RuntimeError("No LLM provider configured")

    def _anthropic_generate(self, *, system: str, prompt: str, temperature: float = 0.0) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=self._resolved_model(),
            max_tokens=4096,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _openai_generate(self, *, system: str, prompt: str, temperature: float = 0.0, expect_json: bool = True) -> str:
        import openai

        client = openai.OpenAI(api_key=settings.openai_api_key)
        kwargs: dict[str, Any] = {
            "model": self._resolved_model(),
            "temperature": temperature,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _gemini_generate(self, *, system_instruction: str, prompt: str, temperature: float = 0.0) -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        model = self._resolved_model()
        url = f"{settings.gemini_base_url}/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        candidates = body.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {body}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if "text" in part)
        if not text:
            raise RuntimeError(f"Gemini returned no text parts: {body}")
        return text

    # ------------------------------------------------------------------
    # Domain methods
    # ------------------------------------------------------------------
    def generate_hypotheses(self, product_name: str, product_type: str) -> list[Hypothesis]:
        provider = self._resolved_provider()
        if provider != "placeholder":
            try:
                system = (
                    "You are a pharmacovigilance scientist generating safety investigation hypotheses.\n\n"
                    "TASK: Generate 4-5 clinically plausible, testable safety signal hypotheses for the "
                    "given product using publicly available FDA adverse event data.\n\n"
                    "Each hypothesis must:\n"
                    "- Be specific and testable with disproportionality or trend analysis\n"
                    "- Include a clear clinical rationale\n"
                    "- Specify the statistical method: prr, ror, ebgm, or trend\n"
                    "- Cover different aspects of the product's safety profile\n\n"
                    "Mark exactly ONE hypothesis as 'selected' (the most impactful to test first) "
                    "and the rest as 'pending'.\n\n"
                    "Return ONLY valid JSON: an array of objects with keys: "
                    "id (string like 'h1'), title, rationale, method (prr|ror|ebgm|trend), "
                    "status (selected|pending)."
                )
                prompt = (
                    f"Generate safety signal hypotheses for:\n"
                    f"  Product name: {product_name}\n"
                    f"  Product type: {product_type}\n"
                    f"  Data source: {'FAERS (FDA Adverse Event Reporting System)' if product_type == 'drug' else 'MAUDE (Manufacturer and User Facility Device Experience)'}\n\n"
                    "Consider adverse event trends, disproportionate reporting of serious outcomes, "
                    "potential label gaps, and comparisons against the product's therapeutic class."
                )
                text = self._generate(system=system, prompt=prompt, temperature=settings.agent.llm_temperature_hypothesis)
                parsed = self._extract_json(text)
                if isinstance(parsed, dict) and "hypotheses" in parsed:
                    parsed = parsed["hypotheses"]
                if isinstance(parsed, list) and parsed:
                    return [
                        Hypothesis(
                            id=str(item.get("id", f"h{i + 1}")),
                            title=str(item.get("title", "")).strip(),
                            rationale=str(item.get("rationale", "")).strip(),
                            method=str(item.get("method", "trend")).lower(),  # type: ignore[arg-type]
                            status=str(item.get("status", "pending")).lower(),  # type: ignore[arg-type]
                        )
                        for i, item in enumerate(parsed)
                        if item.get("title")
                    ]
            except Exception:
                pass

        # Deterministic fallback
        if product_type == "device":
            return [
                Hypothesis(id="h1", title=f"Are malfunction reports for {product_name} increasing over time?", rationale="Device surveillance starts with temporal worsening of malfunctions in MAUDE.", method="trend", status="selected"),
                Hypothesis(id="h2", title=f"Is injury reporting disproportionately high for {product_name}?", rationale="ROR can flag injury-heavy reporting relative to other observed device event types.", method="ror", status="pending"),
                Hypothesis(id="h3", title=f"Does {product_name} show a shrinkage-adjusted malfunction signal?", rationale="EBGM gives a conservative view when event counts are sparse.", method="ebgm", status="pending"),
                Hypothesis(id="h4", title=f"Is death or serious harm reporting elevated for {product_name}?", rationale="PRR offers an interpretable ratio for severe event concentration.", method="prr", status="pending"),
            ]
        return [
            Hypothesis(id="h1", title=f"Are serious adverse event reports for {product_name} increasing over time?", rationale="Trend analysis is a strong first-pass screen for worsening post-market reporting.", method="trend", status="selected"),
            Hypothesis(id="h2", title=f"Is hospitalization or death reporting disproportionately high for {product_name}?", rationale="PRR estimates whether severe outcomes are concentrated for the product.", method="prr", status="pending"),
            Hypothesis(id="h3", title=f"Does {product_name} exhibit a shrinkage-adjusted safety signal for its leading event term?", rationale="EBGM is conservative and aligns with pharmacovigilance practice.", method="ebgm", status="pending"),
            Hypothesis(id="h4", title=f"Are the reporting odds for the leading serious reaction elevated for {product_name}?", rationale="ROR provides an interpretable odds-based disproportionality estimate.", method="ror", status="pending"),
            Hypothesis(id="h5", title=f"Does {product_name} show potential label gaps among its most reported reactions?", rationale="Cross-reference leading reaction terms against current labeling.", method="prr", status="pending"),
        ]

    def write_code(self, context: dict[str, Any]) -> str:
        product_name = context["product_name"]
        product_type = context["product_type"]
        hypothesis = context["hypothesis"]
        error_feedback = context.get("error_feedback", "")

        provider = self._resolved_provider()
        if provider != "placeholder":
            try:
                system = (
                    "You are an expert Python programmer specializing in FDA data analysis.\n\n"
                    "TASK: Write a self-contained Python 3.9+ script that investigates a safety hypothesis "
                    "by querying the openFDA API.\n\n"
                    "REQUIREMENTS:\n"
                    "- Use only: requests, json, collections, datetime, pathlib, math. "
                    "Optionally matplotlib for plots.\n"
                    "- Query the correct openFDA endpoint with appropriate search parameters.\n"
                    "- Handle API errors gracefully (try/except around requests).\n"
                    "- Compute relevant counts: top adverse event terms, serious outcome distribution, "
                    "reporter types, and a monthly/quarterly timeline.\n"
                    "- Save results to workspace/summary.json with keys: queried_at, endpoint, "
                    "hypothesis_title, hypothesis_method, result_count, top_events (list of [term, count]), "
                    "serious_counts (dict), reporter_counts (dict), timeline (list of [period, count]).\n"
                    "- If matplotlib is available, save a trend plot to workspace/reporting_trend.png.\n"
                    "- Print the summary JSON to stdout.\n"
                    "- Create the workspace/ directory if it doesn't exist.\n\n"
                    "Return ONLY JSON with a single key 'code' containing the complete Python script as a string."
                )
                error_section = ""
                if error_feedback:
                    error_section = (
                        f"\n\nPREVIOUS ATTEMPT FAILED with this error:\n{error_feedback}\n"
                        "Fix the issue in your new script."
                    )
                prompt = (
                    f"Write a Python script to investigate this hypothesis:\n"
                    f"  Product: {product_name} ({product_type})\n"
                    f"  Hypothesis: {hypothesis['title']}\n"
                    f"  Method: {hypothesis['method']}\n"
                    f"  Rationale: {hypothesis['rationale']}\n\n"
                    f"  openFDA endpoint: {'https://api.fda.gov/drug/event.json' if product_type == 'drug' else 'https://api.fda.gov/device/event.json'}\n"
                    f"  Search field: {'patient.drug.openfda.generic_name' if product_type == 'drug' else 'brand_name'}"
                    f"{error_section}"
                )
                text = self._generate(system=system, prompt=prompt, temperature=settings.agent.llm_temperature_code)
                parsed = self._extract_json(text)
                code = parsed.get("code") if isinstance(parsed, dict) else None
                if isinstance(code, str) and "summary.json" in code:
                    return code
            except Exception:
                pass

        # Deterministic fallback
        endpoint = "/drug/event.json" if product_type == "drug" else "/device/event.json"
        query = (
            f'patient.drug.openfda.generic_name:"{product_name}"'
            if product_type == "drug"
            else f'brand_name:"{product_name}"'
        )
        return f'''from __future__ import annotations
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import requests
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

url = "https://api.fda.gov{endpoint}"
params = {{"search": '{query}', "limit": 100}}
try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
except Exception:
    payload = {{"results": []}}
results = payload.get("results", [])

reaction_counts = Counter()
serious_counts = Counter()
reporter_counts = Counter()
date_counts = Counter()
for row in results:
    if "{product_type}" == "drug":
        reactions = row.get("patient", {{}}).get("reaction", [])
        for reaction in reactions:
            term = reaction.get("reactionmeddrapt")
            if term:
                reaction_counts[term] += 1
        for key in ["serious", "seriousnessdeath", "seriousnesshospitalization", "seriousnessdisabling", "seriousnesslifethreatening"]:
            if str(row.get(key, "0")) in {{"1", "True", "true"}}:
                serious_counts[key] += 1
        reporter = row.get("primarysource", {{}}).get("qualification") or "unknown"
        reporter_counts[str(reporter)] += 1
        date = str(row.get("receivedate", ""))[:6]
        if date:
            date_counts[date] += 1
    else:
        term = row.get("event_type")
        if term:
            reaction_counts[term] += 1
            serious_counts[term] += 1
        reporter = row.get("report_source_code") or "unknown"
        reporter_counts[str(reporter)] += 1
        date = str(row.get("date_received", ""))[:6]
        if date:
            date_counts[date] += 1

top = reaction_counts.most_common(10)
timeline = sorted(date_counts.items())
Path("workspace").mkdir(exist_ok=True)
if timeline and plt is not None:
    labels = [item[0] for item in timeline]
    values = [item[1] for item in timeline]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(labels, values, marker="o")
    ax.set_title("Reporting trend")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig("workspace/reporting_trend.png")
output = {{
    "queried_at": datetime.utcnow().isoformat() + "Z",
    "endpoint": "{endpoint}",
    "hypothesis_title": {json.dumps(hypothesis["title"])},
    "hypothesis_method": {json.dumps(hypothesis["method"])},
    "result_count": len(results),
    "top_events": top,
    "serious_counts": dict(serious_counts),
    "reporter_counts": dict(reporter_counts),
    "timeline": timeline,
}}
Path("workspace/summary.json").write_text(json.dumps(output, indent=2))
print(json.dumps(output))
'''

    def write_report(self, context: dict[str, Any]) -> str:
        provider = self._resolved_provider()
        if provider != "placeholder":
            try:
                system = (
                    "You are a senior pharmacovigilance scientist writing an FDA-style safety report.\n\n"
                    "TASK: Write concise, professional report prose from the investigation data provided.\n\n"
                    "REQUIREMENTS:\n"
                    "- Use precise language appropriate for regulatory submissions\n"
                    "- Reference specific numbers, counts, and statistical estimates from the data\n"
                    "- Distinguish between known risks (already in product labeling) and potential new signals\n"
                    "- Include appropriate caveats about FAERS/MAUDE passive surveillance limitations\n"
                    "- Be factual — do not speculate beyond what the data shows\n\n"
                    "Return JSON with keys: summary (string), recommendations (string)."
                )
                return self._generate(
                    system=system,
                    prompt=f"Write report prose from this investigation context:\n{json.dumps(context, indent=2, default=str)}",
                    temperature=settings.agent.llm_temperature_report,
                )
            except Exception:
                pass
        return json.dumps(context, indent=2, default=str)

    def review_report(self, context: dict[str, Any]) -> list[str]:
        issues: list[str] = []

        provider = self._resolved_provider()
        if provider != "placeholder":
            try:
                system = (
                    "You are a pharmacovigilance compliance reviewer.\n\n"
                    "TASK: Review this safety investigation report for quality and compliance.\n\n"
                    "CHECK FOR:\n"
                    "1. Missing required sections (Product identification, Surveillance objective, "
                    "Data sources and methodology, Adverse event summary, Statistical analysis, "
                    "Signal assessment, Limitations, Recommendations, Audit trail appendix)\n"
                    "2. Claims without source citations\n"
                    "3. Statistical interpretations that don't match the data\n"
                    "4. Missing limitations acknowledgments\n"
                    "5. Recommendations inconsistent with signal strength\n\n"
                    "Return JSON with key 'issues': an array of strings describing each problem found. "
                    "Return {\"issues\": []} if the report passes review."
                )
                text = self._generate(
                    system=system,
                    prompt=f"Review this report:\n{json.dumps(context, indent=2, default=str)}",
                    temperature=0.0,
                )
                parsed = self._extract_json(text)
                if isinstance(parsed, dict):
                    llm_issues = parsed.get("issues", [])
                    if isinstance(llm_issues, list):
                        issues.extend(str(i) for i in llm_issues)
            except Exception:
                pass

        # Deterministic structural checks always run
        required_headings = {
            "Product identification",
            "Surveillance objective",
            "Data sources and methodology",
            "Adverse event summary",
            "Statistical analysis",
            "Signal assessment",
            "Limitations",
            "Recommendations",
            "Audit trail appendix",
        }
        observed_headings = {section.get("heading") for section in context.get("report_sections", [])}
        missing = sorted(required_headings - observed_headings)
        if missing:
            issues.append(f"Missing required report sections: {', '.join(missing)}.")
        for section in context.get("report_sections", []):
            heading = section.get("heading")
            if heading == "Limitations":
                continue
            if not section.get("sources"):
                issues.append(f"Section '{heading or 'unknown'}' has no sources.")
            if not section.get("evidence_sentences"):
                issues.append(f"Section '{heading or 'unknown'}' is missing evidence sentences.")
            for sentence in section.get("evidence_sentences", []):
                if not sentence.get("sources"):
                    issues.append(f"Evidence sentence in '{heading or 'unknown'}' is missing sources.")
        if context.get("signals"):
            strongest = max(context["signals"], key=lambda item: item.get("estimate", 0))
            if strongest.get("case_count", 0) < 1:
                issues.append("Strongest signal has no case count.")
        return issues
