from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_api_version: str = "2024-10-21"

    # App
    database_url: str = "sqlite:///./data/hackathon.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    data_dir: str = "./data"

    # Code-collection guardrails (token/size limits for large repos)
    max_files: int = 80
    max_file_chars: int = 8000
    max_total_chars: int = 120000

    # Execution-based scoring (Docker sandbox)
    enable_execution: bool = True
    execution_weight: int = 25
    execution_timeout: int = 240

    # Azure deployment bonus — graded points (0–100 scale) added on top, capped at 100.
    azure_bonus_min: float = 20.0
    azure_bonus_max: float = 30.0

    # Optional admin token — when set, mutating endpoints require X-Admin-Token.
    admin_token: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def azure_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_deployment)

    @property
    def azure_auth_mode(self) -> str:
        """'api_key' when a key is provided, otherwise Entra ID (DefaultAzureCredential)."""
        return "api_key" if self.azure_openai_api_key else "entra"

    @property
    def auth_required(self) -> bool:
        return bool(self.admin_token)


settings = Settings()
