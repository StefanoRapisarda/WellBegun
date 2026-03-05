from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./wellbegun.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"

    model_config = {"env_prefix": "APP_"}


settings = Settings()
