from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level settings loaded from environment variables."""

    app_name: str = "Global Time Coordination Agent"
    app_description: str = "An agent that coordinates time-related tasks across multiple agents."
    default_timezone: str = "UTC"
    llm_provider: str = "local"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "mixtral-8x7b-32768"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
