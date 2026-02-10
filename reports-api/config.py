import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "BionicPRO Reports API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Сервер
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # ClickHouse
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", 9000))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "report_user")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "report_bionicpro_2024")
    CLICKHOUSE_DATABASE: str = os.getenv("CLICKHOUSE_DATABASE", "bionicpro_analytics")
    
    # CORS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Безопасность
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "bionicpro_secret_key_change_in_production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    
    # Пути для отчетов
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "/tmp/bionicpro_reports")
    
    class Config:
        env_file = ".env"

settings = Settings()