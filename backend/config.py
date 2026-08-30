import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONDAY_API_KEY: str = ""
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    GEMINI_API_KEY: str = ""
    AI_MODEL: str = "gemini-2.5-flash"
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    CACHE_TTL: int = 300  # 5 minutes
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
