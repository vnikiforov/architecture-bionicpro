from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DeviceInfo(BaseModel):
    """Информация об устройстве"""
    device_id: str = Field(..., description="ID устройства")
    firmware_version: str = Field(..., description="Версия прошивки")
    total_records: int = Field(..., description="Всего записей телеметрии")
    first_activity: Optional[datetime] = Field(None, description="Первая активность")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")

class UserDevicesResponse(BaseModel):
    """Ответ со списком устройств пользователя"""
    user_id: int = Field(..., description="ID пользователя")
    device_count: int = Field(..., description="Количество устройств")
    devices: List[DeviceInfo] = Field(..., description="Список устройств")
    accessed_by: int = Field(..., description="Кто запросил данные")
    timestamp: datetime = Field(..., description="Время запроса")

class AccessInfo(BaseModel):
    """Информация о доступе"""
    accessed_by: int = Field(..., description="ID пользователя, который запросил данные")
    is_own_data: bool = Field(..., description="Являются ли данные собственными")
    timestamp: datetime = Field(..., description="Время доступа")
    
    class Config:
        json_schema_extra = {
            "example": {
                "accessed_by": 1001,
                "is_own_data": True,
                "timestamp": "2024-03-15T10:00:00"
            }
        }

class ErrorResponse(BaseModel):
    """Стандартизированный ответ об ошибке"""
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[dict] = Field(None, description="Дополнительные детали")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ACCESS_DENIED",
                "message": "Вы можете запрашивать только свои данные.",
                "details": {
                    "requested_user": 1002,
                    "authenticated_user": 1001
                }
            }
        }