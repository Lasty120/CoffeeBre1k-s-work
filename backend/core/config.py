"""Application-wide settings loaded from environment variables or .env file.

Uses pydantic-settings so every field can be overridden via the environment,
which makes the app 12-factor compliant with zero extra code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object for the GEOSCAN Mission Planning API.

    Args:
        PROJECT_NAME (str): Human-readable name shown in Swagger UI.
        API_V1_PREFIX (str): URL prefix for all v1 routes, e.g. '/api/v1'.
        CORS_ORIGINS (list[str]): Allowed CORS origins for browser clients.
        DEBUG (bool): Enables debug-level logging and hot-reload hints.

    Returns:
        Settings: Validated, immutable settings instance.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "GEOSCAN Mission Planning API"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    DEBUG: bool = True


settings = Settings()
