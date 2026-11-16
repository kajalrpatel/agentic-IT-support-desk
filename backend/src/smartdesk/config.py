from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://smartdesk:smartdesk@localhost:5432/smartdesk"
    checkpoint_url: str = "postgresql://smartdesk:smartdesk@localhost:5432/smartdesk"
    auth_mode: Literal["demo", "oidc"] = "demo"
    demo_email: str = "jane.doe@example.com"
    session_secret: SecretStr = SecretStr("")
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    openai_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "smartdesk-development"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_hide_inputs: bool = True
    langsmith_hide_outputs: bool = True
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None
    max_output_tokens: int = 1800
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_project_key: str = ""
    jira_issue_type: str = "Task"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection: str = "smartdesk_v1"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    model_cache_dir: str = ".cache/models"
    candidate_limit: int = 20
    context_limit: int = 5
    reranker_min_score: float | None = None
    knowledge_base_path: Path = Path("../knowledge_base")
    request_timeout_seconds: float = 35
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    max_messages_per_minute: int = 20

    @model_validator(mode="after")
    def secure_configuration(self):
        if self.auth_mode == "demo" and len(self.session_secret.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        if self.environment == "production" and self.auth_mode != "oidc":
            raise ValueError("Production requires OIDC authentication")
        if self.auth_mode == "oidc" and not all(
            [self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url]
        ):
            raise ValueError("OIDC issuer, audience and JWKS URL are required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
