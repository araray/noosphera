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
    json: bool = Field(default=True)
    request_id_header: str = Field(default="X-Request-ID")


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    admin_url: str
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=10)
    connect_timeout_s: int = Field(default=5)


class ProvidersSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    default: str = Field(default="openai")
    # Provider-specific fields arrive in later steps.


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
