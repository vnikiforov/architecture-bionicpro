import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Основные настройки
    APP_NAME: str = "BionicPRO Reports API v2.0"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False)
    
    # Сервер
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000, ge=1, le=65535)
    
    # ClickHouse
    CLICKHOUSE_HOST: str = Field(default="clickhouse")
    CLICKHOUSE_PORT: int = Field(default=9000, ge=1, le=65535)
    CLICKHOUSE_USER: str = Field(default="report_user")
    CLICKHOUSE_PASSWORD: str = Field(default="report_bionicpro_2024")
    CLICKHOUSE_DATABASE: str = Field(default="bionicpro_analytics")
    
    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Преобразует строку в список, удаляя пробелы"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Безопасность
    ENABLE_STRICT_ISOLATION: bool = Field(default=True)
    LOG_ACCESS_VIOLATIONS: bool = Field(default=True)
    AUDIT_LOG_DIR: str = Field(default="/var/log/bionicpro/audit")
    
    # Пути для отчетов
    REPORTS_DIR: str = Field(default="/tmp/bionicpro_reports")
    
    # Настройки токенов
    TOKEN_PREFIX: str = Field(default="user_")

settings = Settings()