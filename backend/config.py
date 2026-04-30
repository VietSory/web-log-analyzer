from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Web Log Analyzer API"
    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False

    database_path: str = "weblog_analyzer.db"

    upload_dir: Path = Path("uploads")
    upload_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
    )

    model_dir: Path = Path("models")

    auth_secret_key: SecretStr = SecretStr(
        "dev-only-change-this-secret-at-least-32-bytes"
    )
    auth_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=120, ge=1, le=100_000)
    auth_rate_limit_requests: int = Field(default=10, ge=1, le=10_000)
    auth_account_failure_limit: int = Field(default=5, ge=1, le=1_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    cors_origins: list[str] = ["http://localhost:8501"]
    cors_allow_credentials: bool = True
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["Authorization", "Content-Type"]

    mail_enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    from_email: str | None = None
    alert_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_security_sensitive_settings(self) -> "Settings":
        secret = self.auth_secret_key.get_secret_value()
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("AUTH_SECRET_KEY must contain at least 32 bytes")
        if self.app_env == "production" and secret.startswith("dev-only-"):
            raise ValueError("production requires a non-default AUTH_SECRET_KEY")

        if self.auth_rate_limit_requests > self.rate_limit_requests:
            raise ValueError(
                "AUTH_RATE_LIMIT_REQUESTS must not exceed RATE_LIMIT_REQUESTS"
            )
        if self.auth_account_failure_limit > self.auth_rate_limit_requests:
            raise ValueError(
                "AUTH_ACCOUNT_FAILURE_LIMIT must not exceed AUTH_RATE_LIMIT_REQUESTS"
            )

        if self.cors_allow_credentials:
            if "*" in self.cors_origins:
                raise ValueError("CORS origins must be explicit when credentials are enabled")
            if "*" in self.cors_methods:
                raise ValueError("CORS methods must be explicit when credentials are enabled")
            if "*" in self.cors_headers:
                raise ValueError("CORS headers must be explicit when credentials are enabled")

        if self.mail_enabled:
            if not self.smtp_user:
                raise ValueError("SMTP_USER is required when mail is enabled")
            if not self.smtp_password.get_secret_value():
                raise ValueError("SMTP_PASSWORD is required when mail is enabled")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
