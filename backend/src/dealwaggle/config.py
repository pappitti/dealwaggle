from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEALWAGGLE_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./.data/dealwaggle.db"
    demo_mode: bool = False
    app_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    jwt_issuer: str = ""
    jwt_audience: str = "dealwaggle"
    jwt_jwks_url: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_phone_number_id: str = ""
    resend_webhook_secret: str = ""
    resend_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_secret_key: str = ""
    stripe_price_id: str = ""
    max_webhook_bytes: int = 1_048_576

    @model_validator(mode="after")
    def production_configuration(self):
        if self.environment == "production":
            if self.demo_mode:
                raise ValueError("Demo authentication is forbidden in production")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
            if not self.jwt_issuer or not self.jwt_jwks_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS JWKS URL and JWT issuer")
            if not self.app_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS app URL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
