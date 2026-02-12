from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
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
    return ReportService(clickhouse_client)

@router.post("/reports", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest = Body(...),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> ReportResponse:
    """
    Генерация отчета по бионическому протезу
    
    ⚠️ ВНИМАНИЕ: Вы можете генерировать отчеты только для себя.
    Поле user_id в запросе должно совпадать с вашим ID из токена.
    """
    try:
        # Дополнительная проверка в endpoint
        if request.user_id != auth_data.get('user_id'):
            logger.error(
                f"Пользователь {auth_data.get('user_id')} "
                f"пытается сгенерировать отчет для {request.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ACCESS_DENIED",
                    "message": "Вы можете генерировать отчеты только для себя.",
                    "requested_user": request.user_id,
                    "authenticated_user": auth_data.get('user_id')
                }
            )
        
        report = report_service.generate_report(request, auth_data)
        
        if request.report_format != ReportFormat.JSON:
            file_path = Path(settings.REPORTS_DIR) / f"{report.report_id}.{request.report_format}"
            if file_path.exists():
                return FileResponse(
                    path=file_path,
                    filename=f"bionicpro_report_{report.user_id}_{report.report_id}.{request.report_format}",
                    media_type=_get_media_type(request.report_format)
                )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ошибка генерации отчета"
            }
        )

@router.get("/reports/{user_id}/summary")
async def get_report_summary(
    user_id: int = Path(..., description="ID пользователя", gt=0),
    period: str = Query("month", regex="^(day|week|month|quarter|year|all)$"),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Быстрое получение сводки по пользователю
    
    ⚠️ ВНИМАНИЕ: Вы можете запрашивать только свои данные.
    user_id в пути должен совпадать с вашим ID.
    """
    try:
        # Проверка, что пользователь запрашивает свои данные
        if auth_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ACCESS_DENIED",
                    "message": "Вы можете запрашивать только свои данные.",
                    "requested_user": user_id,
                    "authenticated_user": auth_data.get('user_id')
                }
            )
        
        # Создаем запрос для сводки
        request = ReportRequest(
            user_id=user_id,
            report_format=ReportFormat.JSON,
            period=period,
            include_prosthesis_data=True,
            include_sales_data=False
        )
        
        report = report_service.generate_report(request, auth_data)
        
        return {
            "user_id": report.user_id,
            "health_score": report.prosthesis_metrics.health_score if report.prosthesis_metrics else None,
            "last_activity": report.prosthesis_metrics.last_activity if report.prosthesis_metrics else None,
            "recommendations": report.recommendations[:3] if report.recommendations else [],
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat()
            },
            "access_info": {
                "accessed_by": auth_data.get('user_id'),
                "is_own_data": True,
                "timestamp": report.generated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ошибка получения сводки"
            }
        )

@router.get("/reports/{user_id}/devices")
async def get_user_devices(
    user_id: int = Path(..., description="ID пользователя", gt=0),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Получение списка устройств пользователя
    
    ⚠️ ВНИМАНИЕ: Вы можете запрашивать только свои устройства.
    """
    try:
        if auth_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ACCESS_DENIED",
                    "message": "Вы можете просматривать только свои устройства."
                }
            )
        
        devices_info = report_service.get_user_device_info(user_id, auth_data.get('user_id'))
        
        return devices_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения устройств: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ошибка получения информации об устройствах"
            }
        )

@router.get("/reports/{user_id}/daily/{date}")
async def get_daily_report(
    user_id: int = Path(..., description="ID пользователя", gt=0),
    date: str = Path(..., regex="^\d{4}-\d{2}-\d{2}$", description="Дата в формате YYYY-MM-DD"),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Получение ежедневного отчета по использованию протеза
    
    ⚠️ ВНИМАНИЕ: Вы можете запрашивать только свои ежедневные отчеты.
    """
    try:
        # Проверка доступа
        if auth_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ACCESS_DENIED",
                    "message": "Вы можете запрашивать только свои ежедневные отчеты."
                }
            )
        
        from datetime import datetime
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # В реальном проекте здесь будет запрос к данным за конкретный день
        # Для учебных целей возвращаем пример с информацией о доступе
        
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
            "access_info": {
                "accessed_by": auth_data.get('user_id'),
                "is_own_data": True,
                "timestamp": datetime.now().isoformat()
            },
            "notes": "✅ Это ваш отчет. Данные доступны только вам."
        }
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_DATE_FORMAT",
                "message": "Неверный формат даты. Используйте YYYY-MM-DD"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения ежедневного отчета: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ошибка получения ежедневного отчета"
            }
        )

@router.get("/reports/me/summary")
async def get_my_summary(
    period: str = Query("month", regex="^(day|week|month|quarter|year|all)$"),
    auth_data: Dict[str, Any] = Depends(),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Получение сводки по текущему пользователю (удобный endpoint)
    
    🔒 Автоматически использует ваш ID из токена.
    """
    try:
        user_id = auth_data.get('user_id')
        
        request = ReportRequest(
            user_id=user_id,
            report_format=ReportFormat.JSON,
            period=period,
            include_prosthesis_data=True,
            include_sales_data=False
        )
        
        report = report_service.generate_report(request, auth_data)
        
        return {
            "user_id": user_id,
            "health_score": report.prosthesis_metrics.health_score if report.prosthesis_metrics else None,
            "last_activity": report.prosthesis_metrics.last_activity if report.prosthesis_metrics else None,
            "recommendations": report.recommendations[:3] if report.recommendations else [],
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat()
            },
            "note": "Это ваши данные. Для доступа к данным других пользователей обратитесь к администратору."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ошибка получения вашей сводки"
            }
        )

def _get_media_type(format: ReportFormat) -> str:
    """Получение MIME типа для формата"""
    media_types = {
        ReportFormat.CSV: "text/csv",
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.PDF: "application/pdf",
        ReportFormat.JSON: "application/json"
    }
    return media_types.get(format, "application/octet-stream")