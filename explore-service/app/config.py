"""Application configuration for cloud explore service."""

import os
from typing import List
from pydantic_settings import BaseSettings


def parse_cors_origins(value: str) -> List[str]:
    """Parse CORS origins from string to list."""
    if not value or value.strip() == "":
        return ["*"]
    return [origin.strip() for origin in value.split(",")]


class Settings(BaseSettings):
    """Application settings."""

    APP_NAME: str = "Style Transfer Explore Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/style_transfer_explore"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/style_transfer_explore"

    # File storage
    UPLOAD_DIR: str = "./explore_uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    # CORS
    CORS_ORIGINS: str = "*"

    # Security
    SECRET_KEY: str = "explore-service-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return parse_cors_origins(self.CORS_ORIGINS)

    @property
    def adapters_dir(self) -> str:
        """Directory for adapter uploads."""
        return os.path.join(self.UPLOAD_DIR, "adapters")

    @property
    def training_data_dir(self) -> str:
        """Directory for training data uploads."""
        return os.path.join(self.UPLOAD_DIR, "training_data")


settings = Settings()
