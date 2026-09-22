from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Without this line, BaseSettings only reads real environment variables
    # and silently ignores your .env file.
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Book Store API"
    debug: bool = False
    database_url: str = "sqlite:///./bookstore.db"

    # No default, on purpose: the app refuses to start without a real key.
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


settings = Settings()