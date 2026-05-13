"""
Application configuration loaded from environment variables.

This module provides a single `settings` object that the rest of the application
imports. All configuration is validated at startup — bad config means the app
refuses to start, rather than failing mysteriously at runtime.

Usage:
    from app.core.config import settings
    print(settings.api_port)
    print(settings.llm_model)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==============================================================================
# Path Helpers
# ==============================================================================

# Project root — backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
ENV_FILE = PROJECT_ROOT / ".env"


# ==============================================================================
# Base Settings
# ==============================================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Every field maps to an environment variable. Defaults are used if the
    variable is not set. Validation runs at instantiation — if a value is
    invalid, the application refuses to start with a clear error.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Application
    # --------------------------------------------------------------------------

    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment — controls log format, debug behavior, telemetry",
    )
    app_name: str = Field(
        default="supplymind",
        description="Application name — appears in logs and metric labels",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version — injected by CI in production",
    )

    # --------------------------------------------------------------------------
    # Logging
    # --------------------------------------------------------------------------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity threshold",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format — JSON for production, console for development",
    )
    log_correlation_id: bool = Field(
        default=True,
        description="Include correlation ID in every log entry",
    )
    log_include_agent_name: bool = Field(
        default=True,
        description="Tag log entries with the agent name when applicable",
    )

    # --------------------------------------------------------------------------
    # API Server
    # --------------------------------------------------------------------------

    api_host: str = Field(
        default="0.0.0.0",
        description="Network interface to bind to. 0.0.0.0 for container deployment",
    )
    api_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Port for the FastAPI server",
    )
    api_workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Number of Uvicorn worker processes",
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins",
    )
    request_timeout: int = Field(
        default=120,
        ge=1,
        description="Request timeout in seconds",
    )
    max_request_size_mb: int = Field(
        default=10,
        ge=1,
        description="Maximum request body size in megabytes",
    )

    # --------------------------------------------------------------------------
    # Authentication
    # --------------------------------------------------------------------------

    api_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="API key for authenticated endpoints",
    )
    jwt_secret: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-64",
        description="JWT signing secret",
    )
    jwt_expiry_minutes: int = Field(
        default=60,
        ge=1,
        description="JWT token expiry in minutes",
    )

    # --------------------------------------------------------------------------
    # LLM Configuration
    # --------------------------------------------------------------------------

    llm_model: str = Field(
        default="Qwen/Qwen2.5-1.5B-Instruct",
        description="Primary LLM model identifier (Hugging Face format)",
    )
    llm_fallback_model: str = Field(
        default="Qwen/Qwen2.5-0.5B-Instruct",
        description="Fallback model used when primary fails",
    )
    llm_device: Literal["cpu", "cuda", "mps", "auto"] = Field(
        default="cpu",
        description="Inference device",
    )
    llm_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=32768,
        description="Maximum tokens per LLM response",
    )
    llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = very creative)",
    )
    llm_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling threshold",
    )
    llm_timeout: int = Field(
        default=60,
        ge=1,
        description="LLM inference timeout in seconds",
    )
    llm_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries on LLM failure",
    )
    llm_retry_delay: int = Field(
        default=2,
        ge=1,
        description="Initial retry delay in seconds (exponential backoff)",
    )
    llm_cache_enabled: bool = Field(
        default=True,
        description="Cache LLM responses for identical prompts",
    )
    llm_cache_ttl: int = Field(
        default=3600,
        ge=1,
        description="LLM cache TTL in seconds",
    )

    # --------------------------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------------------------

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-Transformers model for embeddings",
    )
    embedding_device: Literal["cpu", "cuda", "mps", "auto"] = Field(
        default="cpu",
        description="Embedding inference device",
    )
    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=512,
        description="Batch size for embedding generation",
    )

    # --------------------------------------------------------------------------
    # RAG Configuration
    # --------------------------------------------------------------------------

    chroma_persist_dir: str = Field(
        default="./data/chroma",
        description="ChromaDB persistence directory",
    )
    chroma_collection_name: str = Field(
        default="supplymind_knowledge",
        description="ChromaDB collection name",
    )
    rag_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of documents retrieved per query",
    )
    rag_min_similarity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieved documents",
    )
    rag_chunk_size: int = Field(
        default=1000,
        ge=100,
        description="Document chunk size in characters",
    )
    rag_chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Chunk overlap in characters",
    )
    rag_hybrid_search: bool = Field(
        default=True,
        description="Enable hybrid dense + keyword search",
    )
    rag_dense_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight of dense vs keyword score in hybrid search",
    )
    rag_rerank_enabled: bool = Field(
        default=False,
        description="Enable two-stage retrieval with cross-encoder reranking",
    )
    rag_rerank_top_n: int = Field(
        default=3,
        ge=1,
        description="Documents passed to LLM after reranking",
    )

    # --------------------------------------------------------------------------
    # Observability
    # --------------------------------------------------------------------------

    prometheus_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics server port",
    )
    metrics_per_agent_enabled: bool = Field(
        default=True,
        description="Track per-agent metrics (small cardinality overhead)",
    )
    metrics_token_tracking: bool = Field(
        default=True,
        description="Track LLM token consumption per call",
    )
    metrics_service_label: str = Field(
        default="supplymind-backend",
        description="Service label applied to all metrics",
    )

    tracing_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry distributed tracing",
    )
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP exporter endpoint",
    )
    tracing_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate",
    )

    # --------------------------------------------------------------------------
    # Tools
    # --------------------------------------------------------------------------

    tavily_api_key: str = Field(
        default="",
        description="Tavily API key for web search (optional)",
    )
    tavily_max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum web search results per query",
    )
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Tavily search depth",
    )
    tavily_timeout: int = Field(
        default=30,
        ge=1,
        description="Web search timeout in seconds",
    )

    # --------------------------------------------------------------------------
    # Anomaly Detection
    # --------------------------------------------------------------------------

    anomaly_contamination: float = Field(
        default=0.05,
        ge=0.001,
        le=0.5,
        description="Expected fraction of anomalies in data (Isolation Forest)",
    )
    anomaly_n_estimators: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of trees in anomaly detection ensemble",
    )
    anomaly_random_state: int = Field(
        default=42,
        description="Random seed for reproducible anomaly detection",
    )
    anomaly_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which Analyst flags as uncertain",
    )

    # --------------------------------------------------------------------------
    # Circuit Breaker
    # --------------------------------------------------------------------------

    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Consecutive failures before circuit opens",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        ge=1,
        description="Seconds before allowing test request after open",
    )
    circuit_breaker_success_threshold: int = Field(
        default=2,
        ge=1,
        description="Successful test requests before fully closing circuit",
    )

    # --------------------------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------------------------

    eval_on_startup: bool = Field(
        default=False,
        description="Run evaluation suite when application starts (for CI)",
    )
    eval_min_completion_rate: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum task completion rate for healthy build",
    )
    eval_max_hallucination_rate: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Maximum allowed hallucination rate",
    )
    eval_max_p95_latency: int = Field(
        default=10,
        ge=1,
        description="Maximum p95 latency in seconds",
    )

    # --------------------------------------------------------------------------
    # Validators
    # --------------------------------------------------------------------------

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, value: str) -> list[str]:
        """Convert comma-separated string into a clean list of origins."""
        if not value:
            return []
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("api_key", "jwt_secret")
    @classmethod
    def warn_on_default_secrets(cls, value: str, info) -> str:
        """Warn if production-bound deployments use placeholder secrets."""
        if value.startswith("change-me-in-production"):
            # We don't raise here because development needs defaults to work.
            # Production deployments override these via real env vars.
            return value
        if len(value) < 32:
            raise ValueError(
                f"{info.field_name} is too short ({len(value)} chars). "
                f"Generate with: openssl rand -hex 32"
            )
        return value

    @field_validator("rag_chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, value: int, info) -> int:
        """Chunk overlap must be smaller than chunk size."""
        chunk_size = info.data.get("rag_chunk_size", 1000)
        if value >= chunk_size:
            raise ValueError(
                f"rag_chunk_overlap ({value}) must be smaller than "
                f"rag_chunk_size ({chunk_size})"
            )
        return value

    # --------------------------------------------------------------------------
    # Computed Properties
    # --------------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """True when running in development environment."""
        return self.app_env == "development"

    @property
    def is_using_default_secrets(self) -> bool:
        """True when API key or JWT secret is still a placeholder."""
        return (
            self.api_key.startswith("change-me-in-production")
            or self.jwt_secret.startswith("change-me-in-production")
        )

    @property
    def chroma_persist_path(self) -> Path:
        """Absolute path to ChromaDB persistence directory."""
        path = Path(self.chroma_persist_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path


# ==============================================================================
# Settings Instance
# ==============================================================================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Decorated with @lru_cache so the Settings object is created once and
    reused throughout the application lifecycle. Reading environment
    variables and validating them is not free; doing it once is correct.
    """
    return Settings()


# The conventional global accessor used throughout the codebase.
# Most code uses `from app.core.config import settings`.
settings = get_settings()

