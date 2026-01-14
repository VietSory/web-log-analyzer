from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Web Log Analyzer API"
    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False

    database_path: str = "weblog_analyzer.db"

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
