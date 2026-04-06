from __future__ import annotations

from dataclasses import dataclass, field
import os


@dataclass
class SignalDetectionConfig:
    prr_threshold: float = 2.0
    chi_square_alpha: float = 0.05
    min_case_count: int = 3
    ebgm_threshold: float = 2.0
    trend_yoy_threshold: float = 0.25


@dataclass
class AgentConfig:
    max_code_retries: int = 3
    max_review_retries: int = 2
    execution_timeout_sec: int = 120
    llm_temperature_hypothesis: float = 0.7
    llm_temperature_code: float = 0.0
    llm_temperature_report: float = 0.0


@dataclass
class ReportConfig:
    require_source_for_every_claim: bool = True
    include_limitations_section: bool = True
    include_audit_trail_appendix: bool = True


@dataclass
class Settings:
    openfda_base_url: str = "https://api.fda.gov"
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_base_url: str = field(default_factory=lambda: os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"))
    llm_model: str = field(default_factory=lambda: os.getenv("SENTINEL_LLM_MODEL", "deterministic-fallback"))
    llm_provider: str = field(default_factory=lambda: os.getenv("SENTINEL_LLM_PROVIDER", "auto"))
    signal_detection: SignalDetectionConfig = field(default_factory=SignalDetectionConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    report: ReportConfig = field(default_factory=ReportConfig)


settings = Settings()
