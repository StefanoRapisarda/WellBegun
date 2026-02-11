from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./log_input_panels.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "APP_"}


settings = Settings()
