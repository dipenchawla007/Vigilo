from __future__ import annotations

from typing import Any, Literal, TypedDict


ProductType = Literal["drug", "device"]
SignalStrength = Literal["none", "weak", "moderate", "strong"]
ReviewDecision = Literal["approve", "request_changes", "reject", "pending"]


class SourceRecord(TypedDict):
    endpoint: str
    query: str
    full_url: str
    record_count: int
    retrieved_at: str
    context: str
    raw_json_path: str


class EvidenceSentence(TypedDict):
    text: str
    sources: list[SourceRecord]
    confidence: float


class ReportSection(TypedDict):
    heading: str
    text: str
    sources: list[SourceRecord]
    evidence_sentences: list[EvidenceSentence]
    confidence: float


class Hypothesis(TypedDict):
    id: str
    title: str
    rationale: str
    method: Literal["prr", "ror", "ebgm", "trend"]
    status: Literal["pending", "selected", "discarded", "completed"]


class ExecutionArtifact(TypedDict):
    filename: str
    kind: Literal["script", "plot", "json", "text"]
    path: str


class ExecutionResult(TypedDict):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[ExecutionArtifact]
    generated_at: str


class StatisticalSignal(TypedDict):
    event_term: str
    method: str
    estimate: float
    lower_ci: float
    upper_ci: float
    p_value: float
    case_count: int
    signal_strength: SignalStrength
    known_in_label: bool


class ProgressEvent(TypedDict):
    node: str
    status: Literal["started", "completed", "retry", "failed"]
    message: str
    timestamp: str


class InvestigationState(TypedDict, total=False):
    investigation_id: str
    product_name: str
    product_type: ProductType
    time_range_years: int
    started_at: str
    status: str
    selected_hypothesis_id: str
    hypotheses: list[Hypothesis]
    generated_code: str
    code_attempts: int
    execution: ExecutionResult
    data_profile: dict[str, Any]
    analysis_summary: dict[str, Any]
    signals: list[StatisticalSignal]
    report_sections: list[ReportSection]
    compliance_issues: list[str]
    review_attempts: int
    human_decision: ReviewDecision
    reviewer_feedback: str
    progress: list[ProgressEvent]
    audit_trail: list[SourceRecord]
    final_markdown: str
    output_paths: list[str]
