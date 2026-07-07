from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    BOT_TOKEN: str
    MODE: str = "polling"
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PORT: int = 8443
    WEBHOOK_LISTEN: str = "0.0.0.0"
    
    GEMINI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    
    DATABASE_PATH: str = "bot_data.db"
    MAX_FILE_SIZE_MB: int = 20
    MAX_VOICE_DURATION_SECONDS: int = 300
    LOG_LEVEL: str = "INFO"
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
