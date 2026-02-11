"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    replicate_api_token: str = ""
    data_dir: Path = Path("./data")

    @property
    def references_dir(self) -> Path:
        """Directory for reference color images."""
        return self.data_dir / "references"

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded infrared images."""
        return self.data_dir / "uploads"

    @property
    def results_dir(self) -> Path:
        """Directory for colorized result images."""
        return self.data_dir / "results"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.references_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
