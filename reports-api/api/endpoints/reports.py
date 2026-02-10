from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from clickhouse_driver import Client
import logging
from pathlib import Path

from models.reports import ReportRequest, ReportResponse, ReportFormat
from services.report_service import ReportService
from database.clickhouse_client import get_clickhouse_client
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

def get_report_service(
    clickhouse_client: Client = Depends(get_clickhouse_client)
) -> ReportService:
    """Dependency для получения сервиса отчетов"""
    return ReportService(clickhouse_client)

@router.post("/reports", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> ReportResponse:
    """
    Генерация отчета по бионическому протезу
    
    - **user_id**: ID пользователя (клиента или сотрудника)
    - **report_format**: Формат отчета (json, csv, excel, pdf)
    - **period**: Период данных
    - **include_prosthesis_data**: Включить данные по протезу
    - **include_sales_data**: Включить данные по продажам
    """
    try:
        report = report_service.generate_report(request, auth_data)
        
        # Если формат не JSON - возвращаем файл
        if request.report_format != ReportFormat.JSON:
            file_path = Path(settings.REPORTS_DIR) / f"{report.report_id}.{request.report_format}"
            if file_path.exists():
                return FileResponse(
                    path=file_path,
                    filename=f"bionicpro_report_{report.user_id}_{report.report_id}.{request.report_format}",
                    media_type=self._get_media_type(request.report_format)
                )
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{user_id}/summary")
async def get_report_summary(
    user_id: int,
    period: str = Query("month", regex="^(day|week|month|quarter|year|all)$"),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Быстрое получение сводки по пользователю
    
    - **user_id**: ID пользователя
    - **period**: Период данных
    """
    try:
        # Проверка доступа
        if auth_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Создаем запрос для сводки
        request = ReportRequest(
            user_id=user_id,
            report_format=ReportFormat.JSON,
            period=period,
            include_prosthesis_data=True,
            include_sales_data=False
        )
        
        report = report_service.generate_report(request, auth_data)
        
        # Возвращаем упрощенную версию
        return {
            "user_id": report.user_id,
            "health_score": report.prosthesis_metrics.health_score if report.prosthesis_metrics else None,
            "last_activity": report.prosthesis_metrics.last_activity if report.prosthesis_metrics else None,
            "recommendations": report.recommendations[:3] if report.recommendations else [],
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{user_id}/daily")
async def get_daily_report(
    user_id: int,
    date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),  # YYYY-MM-DD
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Получение ежедневного отчета по использованию протеза
    """
    try:
        # Проверка доступа
        if auth_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # В реальном проекте здесь будет запрос к данным за конкретный день
        # Для учебных целей возвращаем пример
        
        from datetime import datetime
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        return {
            "user_id": user_id,
            "date": date,
            "usage_hours": 4.5,
            "avg_battery": 78.2,
            "max_temperature": 34.1,
            "error_count": 0,
            "activities": [
                {"time": "08:30", "activity": "Утренние упражнения", "duration_min": 30},
                {"time": "14:00", "activity": "Работа за компьютером", "duration_min": 120},
                {"time": "19:30", "activity": "Прогулка", "duration_min": 60}
            ],
            "notes": "Нормальное использование, температура в пределах нормы"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Ошибка получения ежедневного отчета: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_media_type(self, format: ReportFormat) -> str:
    """Получение MIME типа для формата"""
    media_types = {
        ReportFormat.CSV: "text/csv",
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.PDF: "application/pdf",
        ReportFormat.JSON: "application/json"
    }
    return media_types.get(format, "application/octet-stream")