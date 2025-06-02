# backend/app/config.py
# Configuration settings for the backend application, loaded from environment variables.

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
# In a Docker environment, these will typically be set in docker-compose.yml or Kubernetes config
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Intent ChatBot"
    APP_VERSION: str = "0.1.0"
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/db")
    
    # NLP settings
    NLP_MODEL_NAME: str = os.getenv("NLP_MODEL_NAME", "en_core_web_sm") # Default spaCy model

    # E-commerce API settings (if applicable)
    ECOMMERCE_API_BASE_URL: str | None = os.getenv("ECOMMERCE_API_BASE_URL")
    ECOMMERCE_API_KEY: str | None = os.getenv("ECOMMERCE_API_KEY")

    # Celery settings (if applicable)
    CELERY_BROKER_URL: str | None = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str | None = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"] # Add your frontend URL(s)
    # If you want to allow all origins (less secure, use with caution):
    # CORS_ORIGINS: list[str] = ["*"]

    # JWT settings (if you add authentication)
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key")
    # ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env" # Specifies a .env file to load, if present
        env_file_encoding = 'utf-8'


# Instantiate settings
settings = Settings()

