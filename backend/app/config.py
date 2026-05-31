"""
Nova AI — Application Configuration
Reads from .env file via pydantic-settings
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.3-70b-instruct"

    # Google Gemini (fallback)
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash-latest"

    # PageSpeed Insights
    pagespeed_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./nova_ai.db"

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Reports
    reports_dir: str = "./reports"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def nvidia_available(self) -> bool:
        return bool(self.nvidia_api_key and self.nvidia_api_key != "nvapi-xxxx")

    @property
    def gemini_available(self) -> bool:
        return bool(self.google_api_key and self.google_api_key != "AIzaXXXX")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
