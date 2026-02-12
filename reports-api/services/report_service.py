import logging
import uuid
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import pandas as pd
from clickhouse_driver import Client
from fastapi import HTTPException

from models.reports import (
    ReportRequest, ReportResponse, ReportFormat, TimePeriod,
    ProsthesisMetrics, SalesMetrics
)
from config import settings

logger = logging.getLogger(__name__)

class ReportService:
    """Сервис для работы с отчетами с изоляцией данных"""
    
    def __init__(self, clickhouse_client: Client):
        self.client = clickhouse_client
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_user_access(self, requested_user_id: int, auth_user_id: int) -> None:
        """Валидация доступа пользователя к данным"""
        if requested_user_id != auth_user_id:
            logger.warning(
                f"Попытка доступа к чужим данным: "
                f"пользователь {auth_user_id} пытается получить данные пользователя {requested_user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен. Вы можете запрашивать только свои данные."
            )
    
    def _check_user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя в системе"""
        try:
            # Проверяем в телеметрии
            query = """
            SELECT COUNT(DISTINCT patient_id) 
            FROM bionicpro_analytics.prosthesis_telemetry 
            WHERE patient_id = %(user_id)s
            """
            
            result = self.client.execute(query, {'user_id': user_id})
            return result[0][0] > 0 if result else False
            
        except Exception as e:
            logger.error(f"Ошибка проверки существования пользователя: {e}")
            return False
    
    def _get_period_dates(self, period: TimePeriod) -> Tuple[date, date]:
        """Получение дат начала и конца периода"""
        today = date.today()
        
        if period == TimePeriod.DAY:
            start_date = today
            end_date = today
        elif period == TimePeriod.WEEK:
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == TimePeriod.MONTH:
            start_date = today.replace(day=1)
            end_date = today
        elif period == TimePeriod.QUARTER:
            quarter = (today.month - 1) // 3 + 1
            start_date = date(today.year, 3 * quarter - 2, 1)
            end_date = today
        elif period == TimePeriod.YEAR:
            start_date = date(today.year, 1, 1)
            end_date = today
        else:  # ALL
            start_date = date(2024, 1, 1)
            end_date = today
        
        return start_date, end_date
    
    def _get_prosthesis_metrics_with_validation(
        self, 
        requested_user_id: int,
        auth_user_id: int,
        start_date: date, 
        end_date: date
    ) -> Optional[ProsthesisMetrics]:
        """Получение метрик протеза с проверкой доступа"""
        
        # Проверяем доступ
        self._validate_user_access(requested_user_id, auth_user_id)
        
        # Проверяем существование пользователя
        if not self._check_user_exists(requested_user_id):
            logger.warning(f"Пользователь {requested_user_id} не найден в системе")
            return None
        
        try:
            # Запрос с дополнительной проверкой в WHERE
            query = """
            SELECT 
                device_id,
                avg_battery_level,
                total_usage_hours,
                avg_motor_temp,
                error_count,
                health_score,
                last_measurement
            FROM bionicpro_analytics.prosthesis_health_mart
            WHERE report_date BETWEEN %(start_date)s AND %(end_date)s
            AND device_id IN (
                SELECT DISTINCT device_id 
                FROM bionicpro_analytics.prosthesis_telemetry 
                WHERE patient_id = %(user_id)s
            )
            ORDER BY report_date DESC
            LIMIT 1
            """
            
            params = {
                'user_id': requested_user_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            result = self.client.execute(query, params)
            
            if not result:
                logger.info(f"Нет данных по протезу для пользователя {requested_user_id}")
                return None
            
            row = result[0]
            return ProsthesisMetrics(
                avg_battery_level=float(row[1]),
                total_usage_hours=float(row[2]),
                avg_motor_temperature=float(row[3]),
                error_count=int(row[4]),
                health_score=float(row[5]),
                last_activity=row[6]
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик протеза: {e}")
            return None
    
    def _get_sales_metrics_with_validation(
        self,
        requested_user_id: int,
        auth_user_id: int,
        start_date: date,
        end_date: date
    ) -> Optional[SalesMetrics]:
        """Получение метрик продаж с проверкой роли"""
        
        # Проверяем доступ
        self._validate_user_access(requested_user_id, auth_user_id)
        
        # В реальном проекте здесь должна быть проверка роли пользователя
        # Для учебных целей возвращаем None, так как обычные пользователи
        # не должны видеть данные продаж
        
        logger.info(f"Пользователь {requested_user_id} запросил данные продаж - доступ запрещен")
        return None
    
    def _generate_recommendations(self, metrics: ProsthesisMetrics) -> List[str]:
        """Генерация рекомендаций на основе метрик"""
        recommendations = []
        
        if metrics.avg_battery_level < 50:
            recommendations.append("🔋 Рекомендуется полная зарядка устройства")
        
        if metrics.error_count > 0:
            recommendations.append("⚠️  Обнаружены ошибки в работе устройства")
        
        if metrics.avg_motor_temperature > 40:
            recommendations.append("🌡️  Высокая температура двигателя, дайте устройству остыть")
        
        if metrics.health_score < 60:
            recommendations.append("🚨 Низкий показатель здоровья устройства, требуется диагностика")
        
        if metrics.total_usage_hours < 2:
            recommendations.append("💪 Рекомендуется увеличить время использования для лучшей адаптации")
        
        if not recommendations:
            recommendations.append("✅ Устройство работает в норме, продолжайте использование")
        
        return recommendations
    
    def _get_raw_data_with_validation(
        self, 
        requested_user_id: int,
        auth_user_id: int,
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Получение сырых данных с проверкой доступа"""
        
        # Проверяем доступ
        self._validate_user_access(requested_user_id, auth_user_id)
        
        try:
            # Запрос с явным указанием patient_id для изоляции
            telemetry_query = """
            SELECT 
                toDate(measurement_time) as day,
                avg(battery_level) as avg_battery,
                sum(usage_hours) as daily_usage,
                countIf(error_codes != []) as errors
            FROM bionicpro_analytics.prosthesis_telemetry
            WHERE patient_id = %(user_id)s
            AND measurement_time BETWEEN %(start_date)s AND %(end_date)s + INTERVAL 1 DAY
            GROUP BY day
            ORDER BY day
            """
            
            params = {
                'user_id': requested_user_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            telemetry_data = self.client.execute(telemetry_query, params)
            
            # Преобразуем в удобный формат
            days_data = []
            for row in telemetry_data:
                days_data.append({
                    'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    'avg_battery': float(row[1]) if row[1] else 0.0,
                    'daily_usage': float(row[2]) if row[2] else 0.0,
                    'errors': int(row[3]) if row[3] else 0
                })
            
            return {
                'telemetry_by_day': days_data,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'user_id': requested_user_id,
                'accessed_by': auth_user_id,
                'access_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сырых данных: {e}")
            return {}
    
    def generate_report(
        self, 
        request: ReportRequest, 
        auth_data: Dict[str, Any]
    ) -> ReportResponse:
        """Генерация отчета с проверкой доступа"""
        
        # Проверяем, что пользователь запрашивает свои данные
        if request.user_id != auth_data.get('user_id'):
            logger.warning(
                f"Попытка доступа к чужим данным через POST: "
                f"пользователь {auth_data.get('user_id')} "
                f"пытается получить отчет для {request.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен. Вы можете генерировать отчеты только для себя."
            )
        
        # Получаем период
        start_date, end_date = self._get_period_dates(request.period)
        
        # Генерируем ID отчета
        report_id = f"rep_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Получаем данные с проверкой доступа
        prosthesis_metrics = None
        sales_metrics = None
        
        if request.include_prosthesis_data:
            prosthesis_metrics = self._get_prosthesis_metrics_with_validation(
                requested_user_id=request.user_id,
                auth_user_id=auth_data.get('user_id'),
                start_date=start_date,
                end_date=end_date
            )
        
        if request.include_sales_data:
            sales_metrics = self._get_sales_metrics_with_validation(
                requested_user_id=request.user_id,
                auth_user_id=auth_data.get('user_id'),
                start_date=start_date,
                end_date=end_date
            )
        
        # Генерируем рекомендации
        recommendations = []
        if prosthesis_metrics:
            recommendations = self._generate_recommendations(prosthesis_metrics)
        
        # Собираем сырые данные
        raw_data = None
        if request.report_format == ReportFormat.JSON:
            raw_data = self._get_raw_data_with_validation(
                requested_user_id=request.user_id,
                auth_user_id=auth_data.get('user_id'),
                start_date=start_date,
                end_date=end_date
            )
        
        # Создаем ответ
        response = ReportResponse(
            user_id=request.user_id,
            report_id=report_id,
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            format=request.report_format,
            prosthesis_metrics=prosthesis_metrics,
            sales_metrics=sales_metrics,
            recommendations=recommendations,
            raw_data=raw_data
        )
        
        # Сохраняем отчет в файл если нужно
        if request.report_format != ReportFormat.JSON:
            self._save_report_to_file(response, request.report_format, auth_data.get('user_id'))
        
        # Логируем успешный доступ
        logger.info(
            f"Сгенерирован отчет {report_id} для пользователя {request.user_id} "
            f"(запросил: {auth_data.get('user_id')})"
        )
        
        return response
    
    def _save_report_to_file(self, report: ReportResponse, format: ReportFormat, accessed_by: int):
        """Сохранение отчета в файл с метаданными доступа"""
        try:
            file_path = self.reports_dir / f"{report.report_id}.{format}"
            
            if format == ReportFormat.CSV:
                self._save_as_csv(report, file_path, accessed_by)
            elif format == ReportFormat.EXCEL:
                self._save_as_excel(report, file_path, accessed_by)
            elif format == ReportFormat.PDF:
                self._save_as_pdf(report, file_path, accessed_by)
            
            logger.info(f"Отчет сохранен в файл: {file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения отчета в файл: {e}")
    
    def _save_as_csv(self, report: ReportResponse, file_path: Path, accessed_by: int):
        """Сохранение как CSV с метаданными доступа"""
        data = {
            'Пользователь': [report.user_id],
            'Запросил': [accessed_by],
            'Период': [f"{report.period_start} - {report.period_end}"],
            'Время генерации': [report.generated_at.isoformat()],
            'Доступ': ['Собственные данные' if report.user_id == accessed_by else 'Чужие данные']
        }
        
        if report.prosthesis_metrics:
            metrics = report.prosthesis_metrics.dict()
            for key, value in metrics.items():
                data[f'Протез_{key}'] = [value]
        
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, encoding='utf-8')
    
    def _save_as_excel(self, report: ReportResponse, file_path: Path, accessed_by: int):
        """Сохранение как Excel с метаданными доступа"""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Информация о доступе
            access_data = {
                'Параметр': ['ID пользователя', 'ID отчета', 'Кто запросил', 'Период', 'Доступ'],
                'Значение': [
                    report.user_id,
                    report.report_id,
                    accessed_by,
                    f"{report.period_start} - {report.period_end}",
                    '✅ Собственные данные' if report.user_id == accessed_by else '❌ Чужие данные'
                ]
            }
            pd.DataFrame(access_data).to_excel(writer, sheet_name='Информация о доступе', index=False)
            
            # Метрики протеза
            if report.prosthesis_metrics:
                metrics_data = report.prosthesis_metrics.dict()
                pd.DataFrame({
                    'Метрика': list(metrics_data.keys()),
                    'Значение': list(metrics_data.values())
                }).to_excel(writer, sheet_name='Метрики протеза', index=False)
            
            # Рекомендации
            if report.recommendations:
                pd.DataFrame({
                    'Рекомендации': report.recommendations
                }).to_excel(writer, sheet_name='Рекомендации', index=False)
    
    def _save_as_pdf(self, report: ReportResponse, file_path: Path, accessed_by: int):
        """Сохранение как PDF (упрощенная версия)"""
        access_status = "✅ Собственные данные" if report.user_id == accessed_by else "❌ ЧУЖИЕ ДАННЫЕ (НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП)"
        
        content = f"""
        ОТЧЕТ BIONICPRO
        ================
        
        ИНФОРМАЦИЯ О ДОСТУПЕ:
        --------------------
        ID пользователя: {report.user_id}
        Запросил: {accessed_by}
        Статус доступа: {access_status}
        
        ОБЩАЯ ИНФОРМАЦИЯ:
        ----------------
        ID отчета: {report.report_id}
        Период: {report.period_start} - {report.period_end}
        Сгенерирован: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
        
        МЕТРИКИ ПРОТЕЗА:
        ---------------
        """
        
        if report.prosthesis_metrics:
            metrics = report.prosthesis_metrics.dict()
            for key, value in metrics.items():
                content += f"\n{key}: {value}"
        
        content += "\n\nРЕКОМЕНДАЦИИ:"
        for rec in report.recommendations:
            content += f"\n• {rec}"
        
        content += f"\n\n---\nЭтот отчет предназначен только для пользователя {report.user_id}"
        content += f"\nЗапрошено пользователем {accessed_by} в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        file_path.write_text(content, encoding='utf-8')
    
    def get_user_device_info(self, user_id: int, auth_user_id: int) -> Dict[str, Any]:
        """Получение информации об устройствах пользователя с проверкой доступа"""
        self._validate_user_access(user_id, auth_user_id)
        
        try:
            query = """
            SELECT 
                device_id,
                max(firmware_version) as firmware,
                count() as total_records,
                min(measurement_time) as first_activity,
                max(measurement_time) as last_activity
            FROM bionicpro_analytics.prosthesis_telemetry
            WHERE patient_id = %(user_id)s
            GROUP BY device_id
            ORDER BY last_activity DESC
            """
            
            result = self.client.execute(query, {'user_id': user_id})
            
            devices = []
            for row in result:
                devices.append({
                    'device_id': row[0],
                    'firmware_version': row[1],
                    'total_records': row[2],
                    'first_activity': row[3].isoformat() if row[3] else None,
                    'last_activity': row[4].isoformat() if row[4] else None
                })
            
            return {
                'user_id': user_id,
                'device_count': len(devices),
                'devices': devices,
                'accessed_by': auth_user_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации об устройствах: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ошибка получения информации об устройствах"
            )