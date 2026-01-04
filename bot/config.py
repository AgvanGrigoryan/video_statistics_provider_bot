from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    #Logging
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    # PostgreSQL paramethers	
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Telegram Bot token
    TG_BOT_SECRET_TOKEN: str

    # Gemini API via OpenAI SDK
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Creating DATABASE_URL dynamically
    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        """Generates db_url string for postgres using credentials

        Format: postgresql+asyncpg://user:password@host:port/database
        - postgresql — DB type
        - asyncpg — async driver
        - other — connection parameters

        Returns:
            str: Created database_url string
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Configuration for Pydantic Settings.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()