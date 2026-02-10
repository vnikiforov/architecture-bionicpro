from datetime import date, datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

class ReportFormat(str, Enum):
    """Форматы отчетов"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"

class TimePeriod(str, Enum):
    """Периоды времени для отчетов"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"

class ProsthesisMetrics(BaseModel):
    """Метрики использования протеза"""
    avg_battery_level: float = Field(..., description="Средний уровень заряда, %")
    total_usage_hours: float = Field(..., description="Всего часов использования")
    avg_motor_temperature: float = Field(..., description="Средняя температура двигателя")
    error_count: int = Field(..., description="Количество ошибок")
    health_score: float = Field(..., description="Общий показатель здоровья устройства")
    last_activity: datetime = Field(..., description="Последняя активность")
    
    class Config:
        json_schema_extra = {
            "example": {
                "avg_battery_level": 85.5,
                "total_usage_hours": 24.3,
                "avg_motor_temperature": 32.1,
                "error_count": 1,
                "health_score": 82.5,
                "last_activity": "2024-03-15T08:30:00"
            }
        }

class SalesMetrics(BaseModel):
    """Метрики продаж"""
    total_orders: int = Field(..., description="Всего заказов")
    total_revenue: float = Field(..., description="Общая выручка, руб.")
    avg_order_amount: float = Field(..., description="Средняя сумма заказа, руб.")
    favorite_model: str = Field(..., description="Самая популярная модель")
    completion_rate: float = Field(..., description="Процент успешных сделок")

class ReportRequest(BaseModel):
    """Запрос на генерацию отчета"""
    user_id: int = Field(..., description="ID пользователя")
    report_format: ReportFormat = Field(default=ReportFormat.JSON, description="Формат отчета")
    period: TimePeriod = Field(default=TimePeriod.MONTH, description="Период отчета")
    include_prosthesis_data: bool = Field(default=True, description="Включить данные по протезу")
    include_sales_data: bool = Field(default=False, description="Включить данные по продажам")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('user_id должен быть положительным числом')
        return v

class ReportResponse(BaseModel):
    """Ответ с отчетом"""
    user_id: int = Field(..., description="ID пользователя")
    report_id: str = Field(..., description="Уникальный ID отчета")
    generated_at: datetime = Field(..., description="Время генерации")
    period_start: date = Field(..., description="Начало периода")
    period_end: date = Field(..., description="Конец периода")
    format: ReportFormat = Field(..., description="Формат отчета")
    
    # Данные отчета
    prosthesis_metrics: Optional[ProsthesisMetrics] = None
    sales_metrics: Optional[SalesMetrics] = None
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1001,
                "report_id": "rep_20240315_123456",
                "generated_at": "2024-03-15T10:00:00",
                "period_start": "2024-03-01",
                "period_end": "2024-03-15",
                "format": "json",
                "prosthesis_metrics": {
                    "avg_battery_level": 85.5,
                    "total_usage_hours": 24.3,
                    "avg_motor_temperature": 32.1,
                    "error_count": 1,
                    "health_score": 82.5,
                    "last_activity": "2024-03-15T08:30:00"
                },
                "recommendations": [
                    "Рекомендуется полная зарядка устройства",
                    "Проверьте соединение датчиков"
                ]
            }
        }