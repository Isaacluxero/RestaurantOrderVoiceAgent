"""Application configuration."""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI
    openai_api_key: str

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # Database
    database_url: str

    # Restaurant
    restaurant_name: str = "Mama Marias"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Dashboard Authentication
    dashboard_password: str = "admin123"  # Change this in .env for production
    session_secret_key: str = "change-this-secret-key-in-production"

    # Order Configuration
    tax_rate: float = 0.0925  # Tax rate as decimal (default 9.25%)

    # Speech Configuration
    speech_timeout: str = "auto"  # Twilio speech timeout ("auto" or number of seconds)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

