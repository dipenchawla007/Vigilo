<p align="center">
  <h1 align="center">Vigilo</h1>
  <p align="center"><strong>Autonomous FDA Safety Intelligence Agent</strong></p>
  <p align="center">
    Type a drug name. Get a fully traceable safety investigation — in minutes, not weeks.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/LangGraph-0.2+-green?style=flat-square" />
    <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20GPT--4o%20%7C%20Gemini-orange?style=flat-square" />
    <img src="https://img.shields.io/badge/data-openFDA-red?style=flat-square" />
    <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" />
  </p>
</p>

---

## What is Vigilo?

Vigilo is an **autonomous pharmacovigilance agent** that investigates drug and medical device safety using publicly available FDA data. It replaces weeks of manual analyst work with a fully automated, auditable pipeline that generates safety hypotheses, writes and executes statistical analysis code, detects adverse event signals, and produces a defensible, regulator-ready report — all with every factual claim traced back to a live FDA data source.

**The problem it solves:** Every pharmaceutical company with an approved drug is legally required to continuously monitor its safety after launch. Today, this is overwhelmingly manual — a pharmacovigilance analyst spends 2–4 weeks per assessment querying FAERS, running disproportionality analyses in SAS/R, drafting reports, and seeking expert review. A single assessment costs $50K–$500K when outsourced to a CRO. Vigilo does this in under 15 minutes.

**The market:** The pharmacovigilance market is valued at $9B in 2025, with 72% of work outsourced to contract research organizations. AI-driven PV is growing at 12–15% CAGR. Early adopters have already shown 41% reduction in case-processing time and 30% improvement in data accuracy.

---

## How it Achieves the Goal in Pharma & Drug Discovery

| Traditional Workflow | Vigilo |
|---|---|
| 2–4 weeks per safety assessment | < 15 minutes end-to-end |
| Manual FAERS queries in web UI or bulk downloads | Autonomous API orchestration via openFDA |
| Statistical analysis in SAS/R by specialist | LLM-written Python executed in an isolated sandbox |
| Scattered audit trail — hard to reconstruct | Every claim linked to a reproducible API call |
| CRO cost: $50K–$500K per product per year | ~$0.50 per investigation in LLM API cost |
| Human expert does the analysis | Human expert reviews and approves the analysis |
| Signals missed due to analyst bandwidth | Continuous, portfolio-wide monitoring at scale |

Vigilo shifts the pharmacovigilance analyst from **data operator** to **scientific reviewer** — the highest-value use of their expertise.

---

## Architecture

### System Layers

```
┌──────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                        │
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │  Streamlit UI   │  │  Citation Viewer │  │ PDF Export  │  │
│  │  (launcher +    │  │  (click-to-trace │  │ (FDA-format │  │
│  │   dashboard)    │  │   any claim)     │  │  report)    │  │
│  └─────────────────┘  └──────────────────┘  └─────────────┘  │
├──────────────────────────────────────────────────────────────┤
│                   AGENT LAYER  (LangGraph)                    │
│                                                               │
│   Hypothesize → Write Code → Execute → Analyze →             │
│   Write Report → Compliance Review → Human Gate              │
│        ↑              ↑                    ↑                  │
│        └─── retry ────┘        retry ──────┘                  │
├──────────────────────────────────────────────────────────────┤
│                  DATA LAYER  (openFDA API)                    │
│                                                               │
│  ┌──────────────┐ ┌────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ FAERS        │ │ Drug       │ │ Drug     │ │ Drugs@FDA │  │
│  │ (adverse     │ │ Labels     │ │ Recalls  │ │ (approvals│  │
│  │  events)     │ │ (SPL)      │ │          │ │  history) │  │
│  └──────────────┘ └────────────┘ └──────────┘ └───────────┘  │
│  ┌──────────────┐ ┌────────────┐                              │
│  │ MAUDE        │ │ Device     │   ← Phase 2: Medical Devices │
│  │ (device AEs) │ │ 510(k)     │                              │
│  └──────────────┘ └────────────┘                              │
├──────────────────────────────────────────────────────────────┤
│                INTELLIGENCE LAYER  (LLM)                      │
│                                                               │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │ Claude API   │  │ Prompt         │  │ Compliance Rules  │  │
│  │ (Sonnet 4)   │  │ Templates      │  │ Engine            │  │
│  │ GPT-4o       │  │ (versioned)    │  │ (claim verifier)  │  │
│  │ Gemini       │  │                │  │                   │  │
│  └──────────────┘  └────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

### Agent Pipeline (LangGraph State Machine)

The core of Vigilo is a 7-node directed graph with 2 conditional retry loops and 1 human-in-the-loop interrupt. The entire investigation state is a strongly typed `TypedDict` that flows through every node — nothing is lost, every transition is checkpointed.

```
User input: drug or device name
         │
         ▼
┌─────────────────────────┐
│  1. HYPOTHESIZE         │  LLM generates 3–5 clinically
│                         │  meaningful, testable safety
│                         │  signal hypotheses
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  2. WRITE CODE          │  LLM writes a Python investigation
│                         │  script tailored to the hypothesis,
│                         │  using seed template + openFDA helpers
└────────────┬────────────┘
             ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  3. EXECUTE             │────▶│ Code failed?         │
│     in Docker sandbox   │     │ Retry up to 3×       │
│     (network-restricted │     │ (error fed back to   │
│      to api.fda.gov)    │     │  node 2 for rewrite) │
└────────────┬────────────┘     └─────────────────────┘
             ▼
┌─────────────────────────┐
│  4. ANALYZE             │  Compute signal strength:
│                         │  PRR · ROR · EBGM · trend analysis
│                         │  Cross-reference against drug label
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  5. WRITE REPORT        │  FDA post-market surveillance format.
│                         │  Every factual claim gets a source
│                         │  citation to a live openFDA API call.
└────────────┬────────────┘
             ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  6. COMPLIANCE REVIEW   │────▶│ Unsourced claims?    │
│                         │     │ Rewrite up to 2×     │
│                         │     │ (issues fed back to  │
│                         │     │  node 5 for revision)│
└────────────┬────────────┘     └─────────────────────┘
             ▼
┌─────────────────────────┐
│  7. HUMAN REVIEW GATE   │  LangGraph interrupt_before pause.
│                         │  Expert approves, requests changes,
│                         │  or rejects. Full state is persisted —
│                         │  can resume hours or days later.
└────────────┬────────────┘
             ▼
      PDF safety report
  (traceable, audit-ready)
```

**Why LangGraph?** Three properties make it the right choice over alternatives like AutoGen or CrewAI:

- **Explicit state typing** — the full `InvestigationState` TypedDict flows through the graph; intermediate results cannot be silently lost or corrupted.
- **Deterministic routing** — conditional edges (e.g., "did code execution succeed?") are pure functions on state, not LLM decisions. Pipeline behavior is predictable and testable.
- **Native interrupt support** — `interrupt_before` on the human review node pauses execution and persists state to a checkpointer, allowing resumption without losing any work.

---

### Traceability Model

Traceability is the most important design element. Every sentence in the final report carries a `sources` array linking it to the exact openFDA API call that produced the data:

```python
ReportSection(
    heading="Adverse event summary",
    text="Metformin had 45,231 FAERS reports in the past 5 years...",
    sources=[
        Source(
            endpoint="/drug/event.json",
            query='patient.drug.openfda.generic_name:metformin',
            full_url="https://api.fda.gov/drug/event.json?search=...",
            record_count=45231,
            retrieved_at="2026-03-15T14:22:00Z",
        )
    ],
    confidence=0.95,
)
```

A regulatory officer can click any sentence in the Streamlit UI, see the exact API URL, click through to openFDA, and independently verify the numbers. This is what makes Vigilo defensible in a regulatory audit.

---

### Statistical Signal Detection

Vigilo implements the same signal detection methods the FDA uses internally:

| Method | Threshold | Used by |
|---|---|---|
| **PRR** — Proportional Reporting Ratio | PRR > 2, chi-square p < 0.05, n ≥ 3 | UK MHRA |
| **ROR** — Reporting Odds Ratio | ROR > 2 with 95% CI excluding 1 | Netherlands Lareb |
| **EBGM** — Empirical Bayes Geometric Mean (MGPS) | EBGM > 2 | FDA Sentinel System |
| **Time-series trend** | YoY increase > 25%, p < 0.05 | Internal |
| **Label gap analysis** | AE present in FAERS but absent from approved label | Novel signals only |

The agent automatically selects the appropriate method based on the hypothesis type. The compliance reviewer verifies that the chosen test matches the data characteristics and that the statistical interpretation is sound.

---

### Sandbox Execution Model

LLM-generated Python code runs in an isolated Docker container:

- Python 3.11 with pandas, scipy, matplotlib, numpy, requests
- Network access restricted via iptables to `api.fda.gov` only
- No filesystem access outside `/workspace`
- 120-second execution timeout
- 512 MB memory limit
- stdout, stderr, and all `/workspace` files are captured after execution

The seed experiment template provides openFDA helper functions (paginated fetching, date range construction, MedDRA term lookup, plot utilities). The LLM only modifies the hypothesis-specific section, reducing code generation error surface significantly.

---

## Project Structure

```
vigilo/
├── pyproject.toml
├── README.md
├── Makefile
├── Dockerfile
├── docker-compose.yml
│
├── src/sentinel/
│   ├── graph.py                   # LangGraph state machine definition
│   ├── state.py                   # InvestigationState TypedDict + sub-types
│   ├── config.py                  # API keys, model selection, thresholds
│   │
│   ├── clients/
│   │   ├── openfda.py             # openFDA API wrapper (FAERS, MAUDE, labels, recalls)
│   │   └── llm.py                 # Claude / GPT-4o / Gemini client with retry logic
│   │
│   ├── nodes/
│   │   ├── hypothesize.py         # Node 1: generate safety signal hypotheses
│   │   ├── write_code.py          # Node 2: LLM writes investigation script
│   │   ├── execute.py             # Node 3: Docker sandbox execution
│   │   ├── analyze.py             # Node 4: statistical analysis + signal scoring
│   │   ├── write_report.py        # Node 5: FDA-format report generation
│   │   ├── review.py              # Node 6: compliance verification
│   │   └── human_gate.py          # Node 7: interrupt_before wrapper
│   │
│   ├── templates/
│   │   ├── seed_experiment.py     # Base Python script with openFDA helpers
│   │   ├── prompts.json           # All LLM system prompts (versioned)
│   │   └── report_template.md    # FDA safety report structure
│   │
│   └── stats/
│       ├── disproportionality.py  # PRR, ROR, EBGM implementations
│       ├── trend.py               # Time-series trend detection
│       └── utils.py               # Confidence intervals, p-values
│
├── ui/
│   ├── app.py                     # Streamlit main application
│   ├── pages/
│   │   ├── launcher.py            # Investigation input page
│   │   ├── dashboard.py           # Live progress feed
│   │   └── review.py              # Report review with citation viewer
│   └── components/
│       ├── citation_viewer.py     # Click-to-trace side panel
│       ├── plot_display.py        # Inline plot rendering
│       └── progress_feed.py       # Real-time status updates
│
├── sandbox/
│   ├── Dockerfile                 # Python 3.11 + scientific stack
│   └── iptables_rules.sh          # Network restriction to api.fda.gov
│
└── tests/
    ├── test_openfda_client.py
    ├── test_graph_flow.py
    ├── test_nodes.py
    ├── test_stats.py
    └── fixtures/
        ├── sample_faers_response.json
        └── sample_maude_response.json
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for sandboxed code execution)
- At least one LLM API key (see below)

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run an investigation from the CLI

```bash
PYTHONPATH=src python3 -m sentinel.graph --product-name metformin --product-type drug
```

### Launch the Streamlit UI

```bash
streamlit run ui/app.py
```

### Run tests

```bash
pytest
```

---

## LLM Configuration

Set one of these environment variables to enable LLM-powered investigations:

```bash
# Anthropic Claude (recommended — best instruction following + code generation)
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI GPT-4o
export OPENAI_API_KEY=sk-...

# Google Gemini
export GEMINI_API_KEY=AI...
```

Without any API key, the pipeline uses a **deterministic fallback** that generates template-based hypotheses and code — useful for testing the full flow without LLM costs.

Override model and provider explicitly:

```bash
export VIGILO_LLM_MODEL=claude-sonnet-4-20250514
export VIGILO_LLM_PROVIDER=anthropic
```

---

## Docker

```bash
# Build and run the full UI service
docker compose up vigilo-ui

# Build the sandbox image for isolated code execution
docker build -t vigilo-sandbox ./sandbox
```

---

## Configuration Thresholds

```yaml
signal_detection:
  prr_threshold: 2.0           # PRR above this = statistical signal
  chi_square_alpha: 0.05       # significance level
  min_case_count: 3            # minimum cases required
  ebgm_threshold: 2.0          # EBGM above this = signal
  trend_yoy_threshold: 0.25    # 25% year-over-year increase = trend signal

agent:
  max_code_retries: 3          # code execution retry limit
  max_review_retries: 2        # compliance review retry limit
  execution_timeout_sec: 120   # sandbox timeout
  llm_temperature_hypothesis: 0.7
  llm_temperature_code: 0.0
  llm_temperature_report: 0.0

report:
  require_source_for_every_claim: true
  include_limitations_section: true
  include_audit_trail_appendix: true
```

---

## Report Output Structure

Every investigation produces a structured report following FDA post-market surveillance conventions:

1. **Product identification** — drug name, active ingredient, NDC codes, manufacturer, approval history
2. **Surveillance objective** — hypothesis tested, clinical rationale, time period examined
3. **Data sources & methodology** — endpoints queried, date ranges, statistical methods and rationale, known FAERS limitations
4. **Adverse event summary** — total report count, MedDRA distribution, outcome severity, quarterly trend charts
5. **Statistical analysis** — PRR/ROR/EBGM with confidence intervals, trend regression, comparison against baseline
6. **Signal assessment** — signal strength classification, clinical interpretation, cross-reference against approved label
7. **Limitations** — FAERS reporting biases, under-reporting, inability to establish causation
8. **Recommendations** — follow-up actions with confidence levels

---

## openFDA Data Coverage

### Phase 1 — Drug Safety

| Endpoint | Source | Use |
|---|---|---|
| `/drug/event.json` | FAERS | Primary adverse event signal detection |
| `/drug/label.json` | SPL labels | Known vs. new signal classification |
| `/drug/enforcement.json` | Recalls | Safety signal correlation with recalls |
| `/drug/drugsfda.json` | Drugs@FDA | Approval context and regulatory history |

### Phase 2 — Medical Devices

| Endpoint | Source | Use |
|---|---|---|
| `/device/event.json` | MAUDE | Device adverse event reports |
| `/device/enforcement.json` | Recalls | Device recall history |
| `/device/510k.json` | 510(k) clearances | Predicate comparison |

All data is free, public, requires no PHI agreements, and updates weekly.

---

## Target Users

### Regulatory Affairs Manager at a Small Biotech
Currently outsources PV work to a CRO at $75K–$200K/product/year with 3–6 week turnaround times. Vigilo replaces routine signal detection: type the drug name, review the autonomous investigation, have a defensible report in under an hour.

### Pharmacovigilance Consultant at a CRO
Manages 10–30 monitoring accounts. Vigilo acts as an autonomous first-pass analyst — the consultant reviews and refines output rather than building from scratch, increasing throughput 5–10×.

### VP of Regulatory at a Large Pharma
Oversees a 50+ product portfolio. Vigilo provides consistent methodology and complete traceability across all products, making regulatory audits straightforward.

---

## Competitive Differentiation

Vigilo does **not** compete with case management systems (Veeva Vault, Oracle Argus) or full-service CROs (IQVIA, Parexel). It competes with the manual analyst workflow itself.

The key differentiator is **end-to-end autonomy with traceability**. Existing AI PV tools handle one step of the workflow. Vigilo handles the entire signal detection cycle — from hypothesis generation through statistical analysis to a defensible report — with every claim linked to a reproducible data source. No other tool provides this.

---

## Roadmap

| Phase | Timeline | Milestone |
|---|---|---|
| **Phase 1** — Drug Safety MVP | Weeks 1–6 | Core autonomous pipeline, FAERS signal detection, Streamlit UI, PDF export |
| **Phase 2** — Medical Devices | Weeks 7–10 | MAUDE integration, device hypothesis templates, production deployment |
| **Phase 3** — Traction | Weeks 11–16 | Open-source core release, public demo, buyer conversations, accelerator applications |
| **Phase 4** — Enterprise | Post-funding | Multi-user workspaces, continuous monitoring, internal database integration, SSO/RBAC |

---

## Key Performance Targets

| Metric | Target |
|---|---|
| Pipeline completion rate | > 80% without manual intervention |
| Code execution success (first attempt) | > 70% |
| Code execution success (within 3 retries) | > 90% |
| End-to-end investigation time | < 15 minutes |
| Source traceability coverage | 100% of factual claims |
| Cost per investigation (LLM API) | ~$0.20–$0.50 |

---

## Implementation Notes

- The graph is implemented with LangGraph. LLM adapters auto-detect provider from environment variables and support Claude, GPT-4o, and Gemini with graceful fallback.
- Code execution uses Docker sandbox when available (network-restricted to `api.fda.gov`), with an in-process subprocess fallback for local development.
- The report writer enforces source links at the section level and keeps per-claim traceability metadata in state.
- PDF export uses WeasyPrint; falls back to HTML if system dependencies are unavailable.
- State persistence uses LangGraph MemorySaver in development and PostgreSQL in production for full audit trail and investigation resume.

---

## License

MIT — see [LICENSE](./LICENSE) for details.

---

<p align="center">
  Built to make drug safety monitoring faster, cheaper, and more defensible.<br/>
  <strong>Vigilo</strong> — watching so regulators don't have to wait.
</p>
