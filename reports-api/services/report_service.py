import logging
import uuid
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

import pandas as pd
from clickhouse_driver import Client

from models.reports import (
    ReportRequest, ReportResponse, ReportFormat, TimePeriod,
    ProsthesisMetrics, SalesMetrics
)
from config import settings

logger = logging.getLogger(__name__)

class ReportService:
    """Сервис для работы с отчетами"""
    
    def __init__(self, clickhouse_client: Client):
        self.client = clickhouse_client
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_period_dates(self, period: TimePeriod) -> tuple[date, date]:
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
            start_date = date(2024, 1, 1)  # Начало данных
            end_date = today
        
        return start_date, end_date
    
    def _get_prosthesis_metrics(self, user_id: int, start_date: date, end_date: date) -> Optional[ProsthesisMetrics]:
        """Получение метрик использования протеза из витрины"""
        try:
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
                'user_id': user_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            result = self.client.execute(query, params)
            
            if not result:
                logger.warning(f"Нет данных по протезу для пользователя {user_id}")
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
    
    def _get_sales_metrics(self, user_id: int, start_date: date, end_date: date) -> Optional[SalesMetrics]:
        """Получение метрик продаж (если пользователь - сотрудник отдела продаж)"""
        try:
            # Для учебных целей возвращаем общие метрики
            query = """
            SELECT 
                sum(orders_count) as total_orders,
                sum(total_revenue) as total_revenue,
                avg(avg_order_amount) as avg_order_amount,
                argMax(prosthesis_model, orders_count) as favorite_model,
                avg(completion_rate) as completion_rate
            FROM bionicpro_analytics.sales_mart
            WHERE report_date BETWEEN %(start_date)s AND %(end_date)s
            """
            
            params = {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            result = self.client.execute(query, params)
            
            if not result or not result[0][0]:  # Нет заказов
                return None
            
            row = result[0]
            return SalesMetrics(
                total_orders=int(row[0]) if row[0] else 0,
                total_revenue=float(row[1]) if row[1] else 0.0,
                avg_order_amount=float(row[2]) if row[2] else 0.0,
                favorite_model=str(row[3]) if row[3] else "Нет данных",
                completion_rate=float(row[4]) if row[4] else 0.0
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик продаж: {e}")
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
    
    def _get_raw_data(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Получение сырых данных для отчета"""
        try:
            # Данные телеметрии по дням
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
                'user_id': user_id,
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
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сырых данных: {e}")
            return {}
    
    def generate_report(self, request: ReportRequest, auth_data: Dict[str, Any]) -> ReportResponse:
        """Генерация отчета по запросу"""
        
        # Проверка доступа (в учебных целях проверяем, что user_id совпадает)
        if auth_data.get('user_id') != request.user_id:
            # В реальном проекте здесь должна быть проверка ролей и прав
            logger.warning(f"Попытка доступа к чужим данным: {auth_data.get('user_id')} -> {request.user_id}")
        
        # Получаем период
        start_date, end_date = self._get_period_dates(request.period)
        
        # Генерируем ID отчета
        report_id = f"rep_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Получаем данные
        prosthesis_metrics = None
        sales_metrics = None
        
        if request.include_prosthesis_data:
            prosthesis_metrics = self._get_prosthesis_metrics(request.user_id, start_date, end_date)
        
        if request.include_sales_data:
            sales_metrics = self._get_sales_metrics(request.user_id, start_date, end_date)
        
        # Генерируем рекомендации
        recommendations = []
        if prosthesis_metrics:
            recommendations = self._generate_recommendations(prosthesis_metrics)
        
        # Собираем сырые данные
        raw_data = None
        if request.report_format == ReportFormat.JSON:
            raw_data = self._get_raw_data(request.user_id, start_date, end_date)
        
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
            self._save_report_to_file(response, request.report_format)
        
        logger.info(f"Сгенерирован отчет {report_id} для пользователя {request.user_id}")
        return response
    
    def _save_report_to_file(self, report: ReportResponse, format: ReportFormat):
        """Сохранение отчета в файл"""
        try:
            file_path = self.reports_dir / f"{report.report_id}.{format}"
            
            if format == ReportFormat.CSV:
                self._save_as_csv(report, file_path)
            elif format == ReportFormat.EXCEL:
                self._save_as_excel(report, file_path)
            elif format == ReportFormat.PDF:
                self._save_as_pdf(report, file_path)
            
            logger.info(f"Отчет сохранен в файл: {file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения отчета в файл: {e}")
    
    def _save_as_csv(self, report: ReportResponse, file_path: Path):
        """Сохранение как CSV"""
        data = {
            'Пользователь': [report.user_id],
            'Период': [f"{report.period_start} - {report.period_end}"],
            'Время генерации': [report.generated_at.isoformat()]
        }
        
        if report.prosthesis_metrics:
            metrics = report.prosthesis_metrics.dict()
            for key, value in metrics.items():
                data[f'Протез_{key}'] = [value]
        
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, encoding='utf-8')
    
    def _save_as_excel(self, report: ReportResponse, file_path: Path):
        """Сохранение как Excel"""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Основная информация
            main_data = {
                'Параметр': ['ID пользователя', 'ID отчета', 'Период', 'Сгенерирован'],
                'Значение': [
                    report.user_id,
                    report.report_id,
                    f"{report.period_start} - {report.period_end}",
                    report.generated_at.strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            pd.DataFrame(main_data).to_excel(writer, sheet_name='Общее', index=False)
            
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
    
    def _save_as_pdf(self, report: ReportResponse, file_path: Path):
        """Сохранение как PDF (упрощенная версия)"""
        # В реальном проекте нужно использовать reportlab или другой PDF генератор
        # Здесь просто сохраняем как текстовый файл для учебных целей
        content = f"""
        ОТЧЕТ BIONICPRO
        ================
        
        ID отчета: {report.report_id}
        Пользователь: {report.user_id}
        Период: {report.period_start} - {report.period_end}
        Сгенерирован: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
        
        МЕТРИКИ ПРОТЕЗА:
        """
        
        if report.prosthesis_metrics:
            metrics = report.prosthesis_metrics.dict()
            for key, value in metrics.items():
                content += f"\n{key}: {value}"
        
        content += "\n\nРЕКОМЕНДАЦИИ:"
        for rec in report.recommendations:
            content += f"\n• {rec}"
        
        file_path.write_text(content, encoding='utf-8')