import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "BionicPRO Reports API v2.0"
    VERSION: str = "2.0.0"
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
    ENABLE_STRICT_ISOLATION: bool = os.getenv("ENABLE_STRICT_ISOLATION", "True").lower() == "true"
    LOG_ACCESS_VIOLATIONS: bool = os.getenv("LOG_ACCESS_VIOLATIONS", "True").lower() == "true"
    AUDIT_LOG_DIR: str = os.getenv("AUDIT_LOG_DIR", "/var/log/bionicpro/audit")
    
    # Пути для отчетов
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "/tmp/bionicpro_reports")
    
    # Настройки токенов
    TOKEN_PREFIX: str = os.getenv("TOKEN_PREFIX", "user_")
    
    class Config:
        env_file = ".env"

settings = Settings()