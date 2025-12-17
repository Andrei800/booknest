"""
Конфигурация приложения BookNest
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # База данных - проверяем есть ли /app/data (для Render)
    DATABASE_URL: str = (
        "sqlite:////app/data/booknest.db" 
        if os.path.exists("/app/data") 
        else "sqlite:///./booknest.db"
    )
    
    # API ключи (опционально)
    GOOGLE_BOOKS_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    
    # Приложение
    APP_NAME: str = "BookNest"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки (с кэшированием)"""
    return Settings()
