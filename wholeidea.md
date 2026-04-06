**Autonomous FDA Safety Intelligence Agent**
Version 1.0 | March 2026

---

## Executive summary

Sentinel is an autonomous AI agent that investigates drug and medical device safety using publicly available FDA data. A user types a product name, and the system autonomously generates safety hypotheses, writes and executes statistical analysis code against live FDA databases, produces a traceable safety report, verifies every claim against its source data, and pauses for human expert review before finalizing.

The system replaces manual pharmacovigilance workflows that cost pharmaceutical companies $50K–$500K per product per year in outsourced consulting fees. The pharmacovigilance market is valued at $9 billion in 2025 with 72% of work outsourced to contract research organizations, making it one of the largest addressable markets in healthcare AI.

**One-liner pitch:** Type a drug name, get an autonomous safety investigation with traceable citations to live FDA data — in minutes, not weeks.

---

## 1. Problem statement

### 1.1 The current state of pharmacovigilance

Every pharmaceutical company with an approved drug is legally required to monitor its safety continuously after launch. This post-market surveillance (Phase IV) involves querying adverse event databases, running statistical signal detection analyses, writing safety assessment reports, and filing them with regulators.

Today, this process is overwhelmingly manual. A pharmacovigilance analyst at a biotech company or a contract research organization (CRO) performs the following steps for each safety assessment: queries the FDA Adverse Event Reporting System (FAERS) through a web interface or bulk data download, exports results to spreadsheets or statistical software (SAS, R), manually runs disproportionality analyses (PRR, ROR, EBGM), interprets the results, drafts a safety report, has it reviewed by a senior scientist, and submits it internally or to regulators. A single assessment typically takes 2–4 weeks of analyst time.

### 1.2 Why this is broken

The process has three fundamental problems. First, it doesn't scale. A mid-size pharma company with 20 marketed products needs continuous monitoring across all of them, but most safety teams have 3–5 analysts. Signals get missed because there aren't enough people to look. Second, it's not reproducible. When a regulator asks "how did you arrive at this conclusion?", the analyst has to reconstruct their query parameters, statistical choices, and interpretive reasoning from memory and scattered notebooks. Third, it's slow. By the time a safety signal is detected, investigated, and documented, weeks or months have passed since the adverse events were reported.

### 1.3 The opportunity

72% of pharmacovigilance work is already outsourced to CROs, meaning companies are actively paying external vendors to do this work. The AI-driven pharmacovigilance market is growing at 12–15% CAGR, with 76% of major service providers investing in AI automation tools. AI integration has already demonstrated 41% reduction in case-processing time and 30% improvement in data accuracy in early adopter organizations. The buyers are actively purchasing — this is not a future market.

### 1.4 What Sentinel does differently

Sentinel replaces the manual analyst workflow with an autonomous agent that performs the entire investigation cycle — from hypothesis generation through statistical analysis to report writing — in minutes. Every claim in the output is traceable to a specific API call against FDA public data, creating a complete audit trail. The human expert reviews and approves the final output rather than doing the underlying analysis, shifting their role from data analyst to quality reviewer.

---

## 2. Target users and personas

### 2.1 Primary persona: regulatory affairs manager at a small/mid biotech

**Profile:** Works at a company with 1–5 marketed drugs. Has 1–2 people on the safety team. Currently outsources most pharmacovigilance work to a CRO at $75K–$200K per product per year. Frustrated by slow turnaround times (3–6 weeks per assessment) and limited ability to do ad hoc investigations when a safety question arises.

**Job to be done:** "I need to know if there's a safety signal for our drug — fast — and I need documentation I can defend to regulators."

**How Sentinel helps:** Replaces the CRO for routine signal detection and safety assessments. The regulatory affairs manager types the drug name, reviews the autonomous investigation, and has a defensible report in under an hour instead of waiting weeks.

### 2.2 Secondary persona: pharmacovigilance consultant at a CRO

**Profile:** Senior scientist at a contract research organization who manages 10–30 drug safety monitoring accounts. Spends most of their time on repetitive FAERS queries and boilerplate report writing rather than high-value scientific interpretation.

**Job to be done:** "I want to handle more accounts without hiring more analysts, and I want to focus on the science instead of the data wrangling."

**How Sentinel helps:** Acts as an autonomous first-pass analyst. The consultant reviews and refines Sentinel's output rather than building from scratch, increasing throughput by 5–10x.

### 2.3 Tertiary persona: VP of regulatory at a large pharma company

**Profile:** Oversees pharmacovigilance for a portfolio of 50+ products. Manages a large internal team plus multiple CRO relationships. Concerned about regulatory audit readiness and consistency across assessments.

**Job to be done:** "I need standardized, auditable safety monitoring across our entire portfolio."

**How Sentinel helps:** Provides consistent methodology and complete traceability across all products. Every assessment follows the same statistical framework and report structure, making regulatory audits straightforward.

---

## 3. Product vision and phases

### 3.1 Vision

Become the system of record for AI-driven pharmacovigilance — the tool that every drug safety team uses to continuously monitor, investigate, and document the safety profile of their products.

### 3.2 Phase roadmap

**Phase 1 (weeks 1–6): Drug safety MVP.** The core autonomous agent pipeline using openFDA FAERS data. User inputs a drug name, the system produces a traceable safety report. Drug safety is prioritized because it addresses a $9B market where 72% of work is outsourced and average contract values are $50K–$500K per year.

**Phase 2 (weeks 7–10): Medical device expansion.** Add openFDA MAUDE database support using the same agent pipeline. Devices serve as a compelling demo (simpler data, more visual adverse event patterns) and access a secondary market of approximately $1.5B.

**Phase 3 (weeks 11–16): Traction and fundraising.** Open-source core release, public demo, buyer conversations, accelerator applications, and first academic publication. Target: documented buyer interest and pre-seed readiness.

**Phase 4 (post-funding): Enterprise features.** Multi-user workspaces, continuous monitoring (scheduled automated investigations), integration with internal safety databases, SSO/RBAC, on-premise deployment for data-sensitive organizations.

---

## 4. System architecture

### 4.1 Architecture overview

The system is organized into four layers that separate concerns cleanly.

**Presentation layer** — Streamlit web application providing the investigation launcher, live progress dashboard, and the human review interface with click-to-trace citation viewer.

**Agent layer** — LangGraph state machine with 7 nodes forming the autonomous investigation pipeline. This is the core of the product: a deterministic, checkpointed workflow that produces consistent, auditable results.

**Data layer** — openFDA public API providing access to FAERS (drug adverse events), MAUDE (device adverse events), drug labels, recalls, and approval histories. All data is free, public, requires no authentication, and updates weekly.

**Intelligence layer** — Claude Sonnet 4 (or GPT-4o) as the reasoning engine, with specialized system prompts for each agent node. Temperature set to 0 for deterministic operations, 0.7 for hypothesis generation.

![image.png](attachment:b66238a2-e2be-4a23-b84b-46b207eb1356:image.png)

![image.png](attachment:a2ecabef-a0c7-4e3a-81d0-310c31250b05:image.png)

```

┌─────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                      │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Streamlit UI │  │ Citation      │  │ PDF export   │  │
│  │ (launcher +  │  │ viewer        │  │ (FDA-format  │  │
│  │  dashboard)  │  │ (click-trace) │  │  report)     │  │
│  └──────────────┘  └───────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│                    AGENT LAYER (LangGraph)                │
│                                                          │
│  Hypothesize → Write code → Execute → Analyze →          │
│  Write report → Compliance review → Human gate            │
│       ↑              ↑                    ↑               │
│       └── retry ─────┘       retry ───────┘               │
├─────────────────────────────────────────────────────────┤
│                    DATA LAYER (openFDA API)               │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐ │
│  │ FAERS      │ │ Drug       │ │ Drug     │ │ Drugs@  │ │
│  │ (adverse   │ │ labels     │ │ recalls  │ │ FDA     │ │
│  │  events)   │ │ (SPL)      │ │          │ │         │ │
│  └────────────┘ └────────────┘ └──────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────┤
│                 INTELLIGENCE LAYER (LLM)                 │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Claude API   │  │ Prompt        │  │ Compliance   │  │
│  │ (Sonnet 4)   │  │ templates     │  │ rules engine │  │
│  └──────────────┘  └───────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 LangGraph agent pipeline

The core pipeline is a directed graph with 7 nodes, 2 conditional retry loops, and 1 human-in-the-loop interrupt.

![image.png](attachment:2095345c-3f50-4b4e-89e0-b39686c675a8:image.png)

```
User input (drug name)
       │
       ▼
┌─────────────────────┐
│ 1. HYPOTHESIZE      │  LLM generates 3–5 testable
│    safety signals    │  safety signal hypotheses
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. WRITE CODE       │  LLM writes Python script
│    for openFDA API  │  to test the hypothesis
└──────────┬──────────┘
           ▼
┌─────────────────────┐     ┌──────────────┐
│ 3. EXECUTE          │────▶│ Code failed? │
│    in sandbox       │     │ Retry (max 3)│
└──────────┬──────────┘     └──────┬───────┘
           │                       │ feeds error
           │                       │ back to node 2
           ▼                       ▼
┌─────────────────────┐
│ 4. ANALYZE          │  Compute signal strength:
│    results          │  PRR, trends, p-values
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5. WRITE REPORT     │  FDA-format sections,
│    with citations   │  every claim sourced
└──────────┬──────────┘
           ▼
┌─────────────────────┐     ┌──────────────┐
│ 6. COMPLIANCE       │────▶│ Claims       │
│    REVIEW           │     │ unverified?  │
└──────────┬──────────┘     │ Rewrite (x2) │
           │                └──────┬───────┘
           │                       │ feeds issues
           │                       │ back to node 5
           ▼
┌─────────────────────┐
│ 7. HUMAN REVIEW     │  LangGraph interrupt_before
│    GATE             │  Streamlit UI pause
└──────────┬──────────┘
           ▼
    PDF safety report
    (traceable output)
```

**Design rationale for LangGraph:** Three properties make LangGraph the right choice over alternatives like AutoGen or CrewAI. First, explicit state typing — the entire investigation state is a TypedDict that flows through the graph, making it impossible for intermediate results to be lost or corrupted. Second, deterministic routing — conditional edges (e.g., "did the code execute successfully?") are pure functions on state, not LLM decisions, so the pipeline behavior is predictable and testable. Third, native interrupt support — `interrupt_before` on the human review node pauses execution and persists the full state to a checkpointer, allowing the investigation to be resumed hours or days later without losing any work.

### 4.3 Data model and traceability

The state object (`InvestigationState`) is the single source of truth for every investigation. It carries all inputs, intermediate results, and outputs through the pipeline. The full state is checkpointed at every node transition, creating a complete audit trail.

The traceability model is the most important design element. Every sentence in the final report contains a `sources` array linking it to specific openFDA API calls:

```
ReportSection:
  heading: str           # "Adverse event summary"
  text: str              # "Metformin had 45,231 FAERS reports..."
  sources:
    - endpoint: "/drug/event.json"
      query: "patient.drug.openfda.generic_name:metformin"
      full_url: "https://api.fda.gov/drug/event.json?search=..."
      record_count: 45231
      retrieved_at: "2026-03-15T14:22:00Z"
  confidence: 0.95
```

When a regulatory officer clicks any sentence in the Streamlit UI, they see the exact API URL that produced the data. They can click through to the openFDA website and verify the numbers independently. This is what makes Sentinel defensible in a regulatory audit — every claim has a reproducible source.

### 4.4 openFDA data layer

**Phase 1 endpoints (drug safety):**

| Endpoint | Data source | Use case |
| --- | --- | --- |
| `/drug/event.json` | FAERS | Primary adverse event signal detection. Millions of reports with patient demographics, drug info, reaction terms (MedDRA), outcomes. Updated quarterly. |
| `/drug/label.json` | SPL labels | Cross-referencing known vs. new signals. If an adverse event is already in the drug's label, it's a known risk — not a new signal. |
| `/drug/enforcement.json` | Recalls | Correlation analysis. Did a safety signal precede or coincide with a recall? |
| `/drug/drugsfda.json` | Approvals | Context. When was the drug approved? What's its regulatory history? |

**Phase 2 endpoints (device safety):**

| Endpoint | Data source | Use case |
| --- | --- | --- |
| `/device/event.json` | MAUDE | Device adverse event reports — deaths, injuries, malfunctions |
| `/device/enforcement.json` | Recalls | Device recall history and classification |
| `/device/510k.json` | Clearances | Pre-market clearance data for predicate comparison |

All openFDA endpoints are free, public, require no authentication for basic queries (API key optional for higher rate limits), and are updated weekly. No data use agreements, no PHI, no HIPAA concerns.

### 4.5 Statistical methods

Sentinel implements established pharmacovigilance signal detection methods that the FDA itself uses:

**Proportional Reporting Ratio (PRR):** Measures whether a specific adverse event is reported more frequently for the target drug than for all other drugs in the database. A PRR > 2 with chi-square p < 0.05 and at least 3 cases is the standard threshold for a statistical signal (adopted from the UK MHRA's criteria).

**Reporting Odds Ratio (ROR):** Similar to PRR but uses an odds ratio framework, making it more robust for rare events and easier to compute confidence intervals. Used by the Netherlands Pharmacovigilance Centre (Lareb).

**Empirical Bayes Geometric Mean (EBGM):** The Multi-item Gamma-Poisson Shrinker (MGPS) method used by the FDA's own Sentinel System. Accounts for multiple comparisons and provides more conservative signal estimates. EBGM > 2 indicates a signal.

**Time-series trend analysis:** Linear regression on quarterly or monthly adverse event counts. Year-over-year increase > 25% with statistical significance (p < 0.05) flags an upward trend warranting investigation.

**Drug-label cross-referencing:** Compares detected adverse events against the drug's FDA-approved label (via `/drug/label.json`). Events already listed in the label's "Adverse Reactions" section are classified as known risks. Events NOT in the label are classified as potential new signals — the highest-value finding for safety teams.

The agent selects the appropriate statistical test based on the hypothesis type. The compliance reviewer verifies that the chosen test matches the data characteristics and that the interpretation is statistically sound.

### 4.6 Sandbox execution model

Generated Python code runs in an isolated Docker container with the following constraints:

- Python 3.11 with pandas, scipy, matplotlib, requests, numpy pre-installed
- Network access restricted via iptables to `api.fda.gov` only — cannot call any other external service
- No filesystem access outside the `/workspace` directory
- 120-second execution timeout (most investigations complete in 30–60 seconds)
- 512MB memory limit
- stdout, stderr, and all files in `/workspace` are captured after execution

The seed experiment template provides helper functions for common openFDA query patterns: paginated fetching, date range construction, MedDRA term lookup, and basic plotting utilities. The LLM modifies the "investigation section" of the template to implement hypothesis-specific logic, reducing the surface area for code generation errors.

### 4.7 Report output structure

Every investigation produces a structured report following FDA post-market surveillance conventions:

1. **Product identification** — drug name, active ingredient, NDC codes, manufacturer, approval date and history from Drugs@FDA
2. **Surveillance objective** — the specific hypothesis tested, clinical rationale, time period examined
3. **Data sources and methodology** — which openFDA endpoints were queried, date ranges, inclusion/exclusion criteria, statistical methods selected and why, known limitations of FAERS passive surveillance
4. **Adverse event summary** — total report count, distribution by event type (MedDRA preferred terms), outcome severity breakdown (hospitalization, death, disability, other), reporting trends over time (quarterly bar chart), reporter type distribution (healthcare professional vs. consumer)
5. **Statistical analysis** — PRR/ROR/EBGM calculations with confidence intervals, trend regression results, seasonal decomposition if applicable, comparison against baseline rates
6. **Signal assessment** — signal strength classification (none / weak / moderate / strong), clinical interpretation, cross-reference against known safety profile from drug label, comparison with similar drugs in the same therapeutic class
7. **Limitations** — FAERS reporting biases (stimulated reporting, Weber effect, notoriety bias), potential under-reporting, inability to establish causation from passive surveillance, confounding factors, single-source limitation
8. **Recommendations** — suggested follow-up actions (further investigation with enhanced data, label review, no action needed), confidence level of recommendation

---

## 5. User experience flow

### 5.1 Investigation launcher

The entry point is deliberately simple. A single text input field with a prompt: "Enter a drug or device name to investigate." Below it, two optional controls: a time range selector (defaulting to 5 years) and a product type toggle (drug / device). A "Start investigation" button triggers the pipeline.

### 5.2 Live investigation dashboard

Once an investigation starts, the user sees a real-time progress feed. Each agent node reports its status as it completes: "Generating hypotheses... 5 hypotheses created." "Writing analysis code for hypothesis: 'Are GI adverse events for metformin increasing year-over-year?'" "Executing code... fetched 45,231 FAERS reports." "Statistical analysis complete. Signal strength: moderate." "Writing safety report... 8 sections drafted." "Compliance review: passed on first attempt."

Progress is streamed via LangGraph's state update callbacks. The user can see intermediate results (raw data counts, preliminary plots) as they are produced, building confidence in the system's work before the final report is ready.

### 5.3 Report review screen

This is the human-in-the-loop gate — the most critical screen in the product. The report is displayed section by section with two interaction modes.

In reading mode, the user sees the full formatted report with generated plots inline. Every sentence that contains a factual claim has a subtle highlight indicator.

In trace mode (activated by clicking any sentence), a side panel opens showing the exact openFDA API URL that produced the data, the raw JSON response (truncated for readability), the statistical computation applied, and a "Verify in browser" link that opens the API URL in a new tab so the reviewer can independently confirm the numbers.

At the bottom, three action buttons: "Approve and generate PDF" (resumes the pipeline to the final output node), "Request changes" (opens a text field for feedback, which loops back to the report writer), and "Reject" (terminates the investigation with an audit log entry).

### 5.4 PDF output

The approved report is compiled to PDF using the FDA safety report structure described in section 4.7. The PDF includes all generated plots, full source citations, and a machine-readable appendix containing the complete audit trail (every API call URL, timestamp, and record count).

---

## 6. Technical requirements

### 6.1 Tech stack

| Component | Technology | Rationale |
| --- | --- | --- |
| Agent orchestration | LangGraph (v0.2+) | Deterministic state graphs, typed state, conditional routing, native `interrupt_before`, checkpointing |
| LLM provider | Anthropic Claude Sonnet 4 | Strongest code generation, best instruction following for structured outputs, cost-effective (~$3/million input tokens) |
| Data source | openFDA API (api.fda.gov) | Free, public, no auth required, maintained by FDA, weekly updates |
| Code sandbox | Docker container via subprocess | Isolated execution, network-restricted to api.fda.gov, stdout/stderr/file capture |
| Web UI | Streamlit | Fastest path to interactive UI for MVP, built-in state management, easy deployment |
| Statistical computing | scipy + pandas + numpy | Standard pharmacovigilance statistics, runs inside the Docker sandbox |
| Plotting | matplotlib | Generated inside sandbox, captured as PNG files |
| State persistence | LangGraph MemorySaver (dev) → PostgreSQL (prod) | Audit trail + investigation resume after human review |
| PDF generation | WeasyPrint or md-to-pdf | Markdown-to-PDF with plot embedding |
| Deployment | Railway (MVP) → AWS ECS (production) | Simple container hosting, scales to production |

### 6.2 Project structure

```
sentinel/
  pyproject.toml
  README.md

  src/sentinel/
    __init__.py
    graph.py                    # LangGraph state machine definition
    state.py                    # InvestigationState TypedDict + sub-types
    config.py                   # API keys, model selection, thresholds

    clients/
      openfda.py                # openFDA API wrapper (FAERS, MAUDE, labels, recalls)
      llm.py                    # Claude/GPT-4 client with retry logic

    nodes/
      hypothesize.py            # Node 1: generate safety signal hypotheses
      write_code.py             # Node 2: LLM writes investigation script
      execute.py                # Node 3: Docker sandbox execution
      analyze.py                # Node 4: statistical analysis + signal scoring
      write_report.py           # Node 5: FDA-format report generation
      review.py                 # Node 6: compliance verification
      human_gate.py             # Node 7: interrupt_before wrapper

    templates/
      seed_experiment.py        # Base Python script with openFDA helpers
      prompts.json              # All LLM system prompts (versioned)
      report_template.md        # FDA safety report structure

    stats/
      disproportionality.py     # PRR, ROR, EBGM implementations
      trend.py                  # Time-series trend detection
      utils.py                  # Confidence intervals, p-values

  ui/
    app.py                      # Streamlit main application
    pages/
      launcher.py               # Investigation input page
      dashboard.py              # Live progress feed
      review.py                 # Report review with citation viewer
    components/
      citation_viewer.py        # Click-to-trace side panel
      plot_display.py           # Inline plot rendering
      progress_feed.py          # Real-time status updates

  sandbox/
    Dockerfile                  # Python 3.11 + scientific stack
    iptables_rules.sh           # Network restriction to api.fda.gov

  tests/
    test_openfda_client.py      # API wrapper tests (mocked)
    test_graph_flow.py          # End-to-end pipeline tests
    test_nodes.py               # Individual node unit tests
    test_stats.py               # Statistical method tests
    fixtures/
      sample_faers_response.json
      sample_maude_response.json

  docker-compose.yml
  Makefile
```

### 6.3 Configuration and thresholds

The system uses configurable thresholds that can be adjusted per investigation or globally:

```yaml
signal_detection:
  prr_threshold: 2.0           # PRR above this = statistical signal
  chi_square_alpha: 0.05       # significance level for chi-square test
  min_case_count: 3            # minimum cases to consider a signal
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

## 7. Implementation plan

### 7.1 Phase 1: Drug safety MVP (weeks 1–6)

**Week 1: Foundation**

- Set up project repository with the structure above
- Implement `InvestigationState` TypedDict and all sub-types in `state.py`
- Build `openfda.py` client with methods for `/drug/event.json` (FAERS), `/drug/label.json`, `/drug/enforcement.json`
- Write unit tests for the openFDA client using mocked responses
- Build Docker sandbox with network restriction
- Deliverable: `python -c "from sentinel.clients.openfda import OpenFDAClient; print(OpenFDAClient().drug_events('metformin'))"` returns live FAERS data

**Week 2: Core pipeline nodes**

- Implement all 7 LangGraph nodes as separate modules
- Write the seed experiment template (`seed_experiment.py`) with openFDA helper functions
- Implement disproportionality statistics (PRR, ROR) in `stats/`
- Wire up the LangGraph state machine in `graph.py` with all edges and conditional routing
- Deliverable: `python -m sentinel.graph --drug metformin` runs the full pipeline in terminal and produces a Markdown report in stdout

**Week 3: Prompt engineering**

- Write and iterate on all 6 LLM system prompts
- Hypothesis generation: test on 20 different drugs, verify hypotheses are clinically meaningful and testable
- Code generation: test on 10 drugs, measure execution success rate (target: >70% on first attempt, >90% within 3 retries)
- Report writing: test on 5 completed investigations, verify every claim has a source citation
- Compliance review: test with intentionally flawed reports to verify rejection behavior
- Deliverable: pipeline completion rate >80% across 20 test drugs

**Week 4: Drug label cross-referencing**

- Add `/drug/label.json` integration to the analysis node
- Implement "known vs. new signal" classification: extract adverse reactions from label text, compare against detected signals
- This is the highest-value feature — identifying adverse events that are NOT in the approved label
- Add "Label gap analysis" section to the report template
- Deliverable: reports correctly distinguish between known risks (in label) and potential new signals (not in label)

**Week 5: Streamlit UI**

- Build the investigation launcher page (single input field + controls)
- Build the live progress dashboard with streaming status updates
- Build the report review page with section-by-section display
- Build the citation viewer component (click sentence → see API source)
- Implement the approve/reject/request-changes workflow connected to LangGraph's interrupt/resume
- Deliverable: full end-to-end flow from browser input to approved PDF

**Week 6: Polish and testing**

- End-to-end testing across 30+ drugs (common drugs, rare drugs, recently approved drugs, withdrawn drugs)
- Error handling: graceful degradation when openFDA returns empty results, rate limit handling with exponential backoff
- PDF export with embedded plots and citation appendix
- README with screenshots, demo video recording
- Deliverable: stable MVP ready for external demos

### 7.2 Phase 2: Device expansion + hardening (weeks 7–10)

**Weeks 7–8: Device safety**

- Add MAUDE endpoint support to `openfda.py`
- Add device-specific hypothesis templates (malfunction trends, death/injury ratios, product class comparisons)
- Adapt the seed experiment template for device queries
- Test across 15+ device types (pacemakers, insulin pumps, hip implants, surgical robots)
- Deliverable: same pipeline works for both drugs and devices with a single toggle

**Weeks 9–10: Production readiness**

- Replace MemorySaver with PostgreSQL for persistent state
- Add basic authentication (API keys or simple login)
- API rate limit management (request queuing, backoff, caching of frequent queries)
- Deploy to Railway or Render
- Monitoring and alerting (investigation failures, API errors)
- Deliverable: production-stable deployment accessible via URL

### 7.3 Phase 3: Traction (weeks 11–16)

**Weeks 11–12: Open source + content**

- Extract the statistical methods and openFDA client into a standalone open-source Python package (`sentinel-core`)
- Write a blog post: "How an AI agent found a safety signal in FDA data in 8 minutes" (use a real, interesting finding from testing)
- Record a 3-minute demo video showing end-to-end flow
- Submit to Hacker News and relevant subreddits (r/bioinformatics, r/pharmacology, r/machinelearning)
- Target: 200+ GitHub stars, 50+ upvotes on HN

**Weeks 13–14: Buyer development**

- Identify 30 biotech companies with 1–5 marketed drugs (the sweet spot: big enough to need PV, small enough to not have a large internal team)
- LinkedIn outreach to regulatory affairs managers and VPs
- Target 10+ discovery conversations
- Prepare a 1-page value proposition document: "Replace your $100K/year CRO PV contract with a $25K/year AI agent"
- Target: 5+ meetings, 2+ expressions of interest

**Weeks 15–16: Accelerator and funding preparation**

- Submit YC application (emphasize: $9B market, 72% outsourced, working product, buyer conversations)
- Submit to healthcare accelerators (Rock Health, StartX Bio, Techstars Healthcare)
- Prepare pre-seed pitch deck (10 slides)
- Submit first academic paper: "Autonomous AI Agent for Pharmacovigilance Signal Detection Using Public FDA Data" → target Drug Safety journal or CHIL conference
- Begin O-1A evidence documentation (original contribution, scholarly articles, judging)

---

## 8. Business model

### 8.1 Pricing tiers

**Free tier (open source):** The `sentinel-core` Python package with statistical methods, openFDA client, and basic command-line investigation runner. No LLM integration, no UI, no report generation. Purpose: community adoption, GitHub traction, developer credibility.

**Professional ($25K/year):** Full autonomous investigation pipeline with Streamlit UI, LLM-powered hypothesis generation and report writing, compliance review, PDF export, up to 50 investigations per month per product. Target: small biotech companies with 1–3 marketed drugs.

**Enterprise ($50K–$100K/year per product):** Everything in Professional plus continuous monitoring (weekly automated investigations), custom hypothesis templates, integration with internal safety databases, dedicated support, on-premise deployment option, SOC 2 compliance. Target: mid-size pharma and large biotechs.

### 8.2 Revenue projections

Conservative scenario: 20 Professional customers at $25K/year by end of Year 1 = $500K ARR. This requires converting approximately 5% of the small biotech companies contacted, which is achievable with a working product and documented ROI.

Growth scenario: 50 Professional + 10 Enterprise customers by end of Year 2 = $1.75M–$2.25M ARR. This requires expanding the sales motion beyond founder-led to include 1–2 SDRs.

### 8.3 Unit economics

The primary cost per investigation is LLM API usage (Claude Sonnet 4). An average investigation uses approximately 50K input tokens and 10K output tokens across all 6 LLM calls, costing roughly $0.20–$0.50 per investigation. At 50 investigations per month per customer, the monthly LLM cost per customer is $10–$25. The gross margin is approximately 95%, similar to other SaaS products.

---

## 9. Competitive landscape

### 9.1 Who Sentinel does NOT compete with

**Veeva Vault Safety / Oracle Argus:** These are case management systems for processing individual adverse event reports (ICSR). They handle intake, triage, coding, and submission of individual cases. Sentinel does not process individual cases — it analyzes aggregate patterns across the entire database.

**Full-service CROs (IQVIA, Parexel, Covance):** These organizations provide end-to-end clinical trial management and pharmacovigilance services including case processing, medical review, and regulatory submissions. Sentinel replaces one specific workflow (signal detection from public data), not the entire PV function.

**Ritivel / Scoop / Entvin:** These YC-backed companies automate FDA submission document drafting (INDs, CTDs, CSRs). Different workflow, different buyer, different data sources.

### 9.2 Who Sentinel competes with

**Manual analyst workflows:** A pharmacovigilance analyst spending 2–4 weeks on FAERS analysis. Sentinel does this in minutes with better reproducibility.

**Boutique PV consulting firms:** Charging $50K–$200K per safety assessment. Sentinel delivers equivalent output at a fraction of the cost with superior traceability.

**Internal safety teams** at under-resourced small/mid biotechs. Sentinel augments a team of 1–2 people to cover monitoring for their entire portfolio.

### 9.3 Differentiation

The key differentiator is end-to-end autonomy with traceability. Existing AI PV tools typically handle one step of the workflow (e.g., case intake automation, or literature screening). Sentinel handles the entire signal detection workflow from hypothesis to defensible report. And every claim in the output links to a reproducible data source, which no other tool provides.

---

## 10. O-1A visa strategy

This project is designed to satisfy 5 of the 8 O-1A extraordinary ability criteria.

**Original contributions of major significance:** An autonomous agent that adapts open-ended AI research frameworks to continuously monitor FDA safety databases — the first system to combine agentic AI with pharmacovigilance signal detection. Evidence: GitHub adoption, hospital/pharma deployments, expert recommendation letters.

**Scholarly articles:** Target publications in Drug Safety (impact factor 3.8), CHIL (Conference on Health, Inference, and Learning), or npj Digital Medicine. Paper: "Autonomous AI Agent for Pharmacovigilance Signal Detection Using Public FDA Data."

**Published material about the beneficiary:** Independent coverage in STAT News, Healthcare IT News, TechCrunch, or Hacker News front page. The "AI finds drug safety signal in FDA data in 8 minutes" angle is inherently newsworthy.

**Judging others' work:** Serve as peer reviewer for Drug Safety, CHIL, MLHC, or NeurIPS health workshops. USCIS now explicitly recognizes GitHub PR reviews for major open-source projects.

**Leading role at a distinguished organization:** Founding CEO of a YC-backed (if accepted) or healthcare-accelerator-backed startup. USCIS recognizes startup founders who contribute intellectual property.

**Timeline:** Begin building evidence immediately. Target O-1A filing at month 12–15 with premium processing (15-day adjudication). Current O-1A approval rate: 93.8%.

---

## 11. Risk register

| Risk | Severity | Likelihood | Mitigation |
| --- | --- | --- | --- |
| openFDA API rate limits or extended downtime | Medium | Low | Exponential backoff, local result caching, graceful degradation with cached data |
| LLM generates incorrect statistical code | High | Medium | Sandbox catches runtime errors, compliance reviewer verifies results, 3-retry loop, seed template reduces error surface |
| LLM hallucinated a safety claim not backed by data | Critical | Medium | Every claim requires an API source URL. Reviewer node rejects unsourced claims. Human gate is the final verification. Triple-layer defense. |
| FAERS data quality issues (under-reporting, duplicates, stimulated reporting) | Medium | High | Mandatory limitations section in every report. Cannot be solved — inherent to passive surveillance. Acknowledged transparently. |
| Competitor builds the same thing faster | Medium | Medium | Speed to market (6-week MVP), open-source traction (community switching costs), customer relationships, deep domain prompt engineering as moat |
| FDA changes API structure or endpoints | Low | Low | Thin adapter layer isolates API specifics from agent logic. Versioned endpoint configuration. |
| Solo founder execution risk | High | Medium | Narrow scope (drug safety signal detection only), resist feature creep, target 6-week MVP, find co-founder with PV domain experience post-MVP |
| Pharma companies slow to adopt AI for regulated workflows | Medium | Medium | Start with non-regulated use case (internal signal screening, not regulatory submissions), build trust through accuracy, expand to regulated use cases after establishing track record |
| LLM costs scale faster than revenue | Low | Low | Current cost ~$0.20–0.50 per investigation. At $25K/year per customer, LLM cost is <1% of revenue. Safe even at 10x higher usage. |

---

## 12. Success metrics and milestones

### Technical milestones (Phase 1, weeks 1–6)

| Metric | Target | Measurement |
| --- | --- | --- |
| Pipeline completion rate | >80% | Investigations producing a valid report without manual intervention, tested across 30+ drugs |
| Code execution success rate | >70% first attempt, >90% within 3 retries | Logged per investigation |
| Compliance review first-pass rate | >60% | Reports passing automated review without rewrite |
| End-to-end investigation time | <15 minutes | Wall clock time from input to approved PDF |
| Source traceability coverage | 100% | Every factual claim in report has an API source |

### Traction milestones (Phase 3, weeks 11–16)

| Metric | Target | Measurement |
| --- | --- | --- |
| GitHub stars (sentinel-core) | >200 | Public repository |
| Documented buyer conversations | 5+ | CRM / conversation notes |
| Letters of intent or pilot agreements | 2+ | Signed documents |
| Paper submissions | 1 | Submitted to peer-reviewed venue |
| Accelerator applications | 2+ | YC + 1 healthcare accelerator |
| Media/community mentions | 3+ | HN, Twitter, blog coverage |

### Pre-seed readiness (month 4–6)

| Requirement | Evidence |
| --- | --- |
| Working product | Live demo URL, recorded video |
| Market validation | Buyer conversations + LOIs |
| Market size | $9B PV market, 72% outsourced (cited sources) |
| Differentiation | No competitor does end-to-end autonomous PV with traceability |
| Team | Solo founder with ML infrastructure background + plan to recruit PV domain co-founder |
| Ask | $300K–$500K pre-seed for 12-month runway |
| Use of funds | 60% founder salary, 20% LLM API costs + infrastructure, 10% conference/travel, 10% legal (incorporation + O-1A) |

---

## 13. Open questions for PRD review

1. Should the MVP support multiple simultaneous investigations, or is one-at-a-time acceptable for launch?
2. What is the minimum viable number of hypothesis types (trend only? PRR only? Or all four methods from day one)?
3. Should the open-source package include LLM integration, or keep it purely statistical with manual query construction?
4. Is Streamlit sufficient for the first 10 customers, or should we plan for a Next.js frontend from the start?
5. Should we pursue FDA engagement (e.g., presenting at an FDA public workshop) as a credibility signal, or is that premature pre-funding?

---

*This document should be treated as a living specification. Update it as implementation reveals new requirements, buyer conversations shift priorities, or competitive dynamics change.*