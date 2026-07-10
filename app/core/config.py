from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: list[str]
    OPENROUTER_API_KEY: str                                  # sk-or-v1-...
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "openai/gpt-4o-mini"                    # default. format: provider/model
    LLM_FALLBACK_MODELS: list[str] = []                      # tried in order if the primary fails
    ALLOWED_MODELS: list[str] = [                            # allowlist — clients may only pick from here
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-haiku-4.5",
        "anthropic/claude-sonnet-4.5",
        "google/gemini-2.5-flash",
    ]
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 2
    SYSTEM_PROMPT: str = "You are a helpful assistant."
    MAX_HISTORY_MESSAGES: int = 20                            # used on the next step
    APP_URL: str = "http://localhost:3000"                    # optional OpenRouter ranking headers
    APP_NAME: str = "ai-chat-backend"
    MAX_TOOL_ITERATIONS: int = 5
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    @model_validator(mode="after")
    def _default_model_must_be_allowed(self) -> "Settings":
        if self.LLM_MODEL not in self.ALLOWED_MODELS:         # fail at boot, not at 3am
            raise ValueError(f"LLM_MODEL '{self.LLM_MODEL}' is not in ALLOWED_MODELS")
        return self
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()