from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    MODEL_NAME: str = "distilbert-base-uncased"
    CONFIDENCE_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"

settings = Settings()