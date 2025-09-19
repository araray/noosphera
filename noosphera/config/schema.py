# FILE: noosphera/config/schema.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServerSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)


class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    level: str = Field(default="INFO")
    json_mode: bool = Field(default=True, alias="json")
    request_id_header: str = Field(default="X-Request-ID")
    sanitize_prompts: bool = Field(default=False)


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    admin_url: str
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=10)
    connect_timeout_s: int = Field(default=5)


class OpenAISettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=False)
    api_key: str | None = Field(default=None)
    base_url: str = Field(default="https:")
    organization: str | None = Field(default=None)
    request_timeout_s: int = Field(default=60, ge=1)
    default_model: str | None = Field(default=None)


class OllamaSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=False)
    host: str = Field(default="http:")
    request_timeout_s: int = Field(default=60, ge=1)
    default_model: str | None = Field(default=None)


class ProvidersSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=False)
    default_provider: str = Field(default="openai")
    default_model: str | None = Field(default=None)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)


class FeatureFlags(BaseModel):
    model_config = ConfigDict(extra="ignore")
    auth_enabled: bool = Field(default=False)


# NEW (Step 1.3): security settings surface
class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    api_key_header: str = Field(default="X-Noosphera-API-Key")


# NEW (Step 1.4): chat settings surface
class ChatSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    history_max_messages: int = Field(default=20, ge=1)
    mock_llm_enabled: bool = Field(default=True)


# NEW (Step 1.6): metrics settings
class MetricsSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=True)
    path: str = Field(default="/metrics")
    include_tenant_label: bool = Field(default=False)


# NEW (Step 1.6): tracing settings
class TracingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=False)
    otlp_endpoint: str | None = Field(default=None)
    sample_ratio: float = Field(default=0.01, ge=0.0, le=1.0)


# NEW (Step 1.6): debug settings
class DebugSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    config_inspect_enabled: bool = Field(default=False)


class Settings(BaseModel):
    """
    Typed, validated configuration envelope. Accepts extra keys to remain
    forward-compatible with later phases (DB, auth, providers).
    """
    model_config = ConfigDict(extra="ignore")
    server: ServerSettings
    logging: LoggingSettings
    database: DatabaseSettings
    providers: ProvidersSettings
    security: SecuritySettings  # NEW (Step 1.3)
    features: FeatureFlags
    chat: ChatSettings  # NEW (Step 1.4)
    metrics: MetricsSettings  # NEW (Step 1.6)
    tracing: TracingSettings  # NEW (Step 1.6)
    debug: DebugSettings  # NEW (Step 1.6)
