from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.email_operator import EmailOperator
import pandas as pd
import requests
from clickhouse_driver import Client
import logging
import json
from typing import Dict, List

# Конфигурация для BionicPRO
BITRIX24_API_URL = "http://bitrix24-api:1080/rest"
MAIN_DB_API_URL = "http://api-bionicpro:8080/api"
CLICKHOUSE_CONFIG = {
    'host': 'clickhouse',
    'port': 8123,
    'user': 'analytics_user',
    'password': 'bionicpro_analytics_2024',
    'database': 'bionicpro_analytics'
}

# ==================== ФУНКЦИИ ДЛЯ СБОРА ДАННЫХ ИЗ CRM ====================
def extract_crm_data():
    """Сбор данных о заказах и клиентах из Битрикс24"""
    logging.info("📥 [BionicPRO] Ежедневный сбор данных из Битрикс24 CRM")
    
    try:
        # Имитация данных для учебных целей (вместо реального API)
        crm_data = {
            'timestamp': datetime.now().isoformat(),
            'orders': [
                {
                    'ID': 1001,
                    'TITLE': 'Заказ протеза BionicPRO V2',
                    'STAGE_ID': 'WON',
                    'OPPORTUNITY': 250000.00,
                    'DATE_CREATE': '2024-03-01',
                    'CONTACT_ID': 2001,
                    'ASSIGNED_BY_ID': 3001,
                    'UF_CRM_PROSTHESIS_MODEL': 'BIONICPRO_V2',
                    'UF_CRM_REGION': 'Москва'
                },
                {
                    'ID': 1002,
                    'TITLE': 'Кастомный протез для спортсмена',
                    'STAGE_ID': 'MANUFACTURING',
                    'OPPORTUNITY': 450000.00,
                    'DATE_CREATE': '2024-03-05',
                    'CONTACT_ID': 2002,
                    'ASSIGNED_BY_ID': 3002,
                    'UF_CRM_PROSTHESIS_MODEL': 'BIONICPRO_CUSTOM',
                    'UF_CRM_REGION': 'Санкт-Петербург'
                }
            ],
            'clients': [
                {
                    'ID': 2001,
                    'NAME': 'Иван',
                    'LAST_NAME': 'Иванов',
                    'EMAIL': 'ivan@example.com',
                    'PHONE': '+79161234567',
                    'UF_CRM_MEDICAL_HISTORY_ID': 'MH-001',
                    'UF_CRM_REGION': 'Москва'
                },
                {
                    'ID': 2002,
                    'NAME': 'Мария',
                    'LAST_NAME': 'Петрова',
                    'EMAIL': 'maria@example.com',
                    'PHONE': '+79162345678',
                    'UF_CRM_MEDICAL_HISTORY_ID': 'MH-002',
                    'UF_CRM_REGION': 'Санкт-Петербург'
                }
            ],
            'production_orders': [
                {
                    'ID': 5001,
                    'TITLE': 'Изготовление BionicPRO V2',
                    'STAGE_ID': 'MANUFACTURING',
                    'UF_CRM_PROSTHESIS_SERIAL': 'BP-2024-001',
                    'UF_CRM_TECHNICIAN_ID': 4001,
                    'UF_CRM_EST_COMPLETION': '2024-03-20'
                }
            ],
            'source': 'bitrix24_crm',
            'etl_batch': f"crm_{datetime.now().strftime('%Y%m%d_%H%M')}"
        }
        
        # Сохраняем сырые данные
        with open('/tmp/bionicpro_crm_raw.json', 'w') as f:
            json.dump(crm_data, f, indent=2, default=str)
        
        logging.info(f"📊 BionicPRO: Собрано {len(crm_data['orders'])} заказов, "
                    f"{len(crm_data['clients'])} клиентов, "
                    f"{len(crm_data['production_orders'])} заказов на производство")
        
        return '/tmp/bionicpro_crm_raw.json'
        
    except Exception as e:
        logging.error(f"❌ Ошибка сбора данных из CRM: {e}")
        raise

def transform_crm_data(**context):
    """Трансформация CRM данных для аналитики"""
    ti = context['ti']
    file_path = ti.xcom_pull(task_ids='extract_crm_data')
    
    logging.info("🔄 [BionicPRO] Трансформация CRM данных")
    
    with open(file_path, 'r') as f:
        crm_data = json.load(f)
    
    # 1. Обработка заказов
    orders_df = pd.DataFrame(crm_data['orders'])
    
    # Добавляем категоризацию по модели протеза
    prosthesis_types = {
        'BIONICPRO_V1': 'Начальный',
        'BIONICPRO_V2': 'Стандарт',
        'BIONICPRO_V3': 'Профессиональный',
        'BIONICPRO_CUSTOM': 'Кастомный'
    }
    
    orders_df['prosthesis_category'] = orders_df['UF_CRM_PROSTHESIS_MODEL'].map(
        lambda x: prosthesis_types.get(x, 'Другая')
    )
    
    # 2. Обработка клиентов (с анонимизацией чувствительных данных)
    clients_df = pd.DataFrame(crm_data['clients'])
    
    # Анонимизация для GDPR/медицинских данных
    if 'EMAIL' in clients_df.columns:
        clients_df['email_hash'] = clients_df['EMAIL'].apply(
            lambda x: hash(str(x)) % 1000000 if pd.notna(x) else 0
        )
        clients_df = clients_df.drop('EMAIL', axis=1)
    
    if 'PHONE' in clients_df.columns:
        clients_df['phone_masked'] = clients_df['PHONE'].apply(
            lambda x: str(x)[:3] + '****' + str(x)[-2:] if pd.notna(x) else ''
        )
        clients_df = clients_df.drop('PHONE', axis=1)
    
    # 3. Обработка заказов на производство
    production_df = pd.DataFrame(crm_data['production_orders'])
    
    # Добавляем статус производства
    production_status = {
        'PREPARATION': 'Подготовка',
        'MANUFACTURING': 'Изготовление',
        'QUALITY_CHECK': 'Контроль качества',
        'COMPLETED': 'Готово'
    }
    
    production_df['production_status_ru'] = production_df['STAGE_ID'].map(
        lambda x: production_status.get(x, 'Неизвестно')
    )
    
    # Сохраняем трансформированные данные
    transformed_data = {
        'orders': orders_df.to_dict('records'),
        'clients': clients_df.to_dict('records'),
        'production': production_df.to_dict('records'),
        'metadata': {
            'transform_date': datetime.now().isoformat(),
            'dag_run_id': context['run_id'],
            'company': 'BionicPRO'
        }
    }
    
    transformed_path = '/tmp/bionicpro_crm_transformed.json'
    with open(transformed_path, 'w') as f:
        json.dump(transformed_data, f, default=str)
    
    logging.info(f"✅ Трансформировано: {len(orders_df)} заказов, "
                f"{len(clients_df)} клиентов, "
                f"{len(production_df)} производственных заказов")
    
    return transformed_path

# ==================== ФУНКЦИИ ДЛЯ СБОРА ДАННЫХ О ПРОТЕЗАХ ====================
def extract_prosthesis_telemetry():
    """Сбор телеметрии с бионических протезов"""
    logging.info("📡 [BionicPRO] Сбор телеметрии с протезов")
    
    try:
        # Имитация данных телеметрии для учебных целей
        telemetry_data = {
            'timestamp': datetime.now().isoformat(),
            'records': [
                {
                    'device_id': 'BP-2024-001',
                    'patient_id': 2001,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'battery_level': 85.5,
                    'usage_hours': 24.3,
                    'motor_temperature': 32.1,
                    'sensor_readings': {'pressure': 45, 'flexion': 78},
                    'error_codes': [],
                    'firmware_version': '2.1.4',
                    'location': {'lat': 55.7558, 'lon': 37.6173}
                },
                {
                    'device_id': 'BP-2024-001',
                    'patient_id': 2001,
                    'timestamp': (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
                    'battery_level': 72.3,
                    'usage_hours': 25.1,
                    'motor_temperature': 35.2,
                    'sensor_readings': {'pressure': 48, 'flexion': 82},
                    'error_codes': [101],
                    'firmware_version': '2.1.4',
                    'location': {'lat': 55.7558, 'lon': 37.6173}
                },
                {
                    'device_id': 'BP-2024-002',
                    'patient_id': 2002,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'battery_level': 91.2,
                    'usage_hours': 8.5,
                    'motor_temperature': 28.7,
                    'sensor_readings': {'pressure': 42, 'flexion': 65},
                    'error_codes': [],
                    'firmware_version': '2.2.0',
                    'location': {'lat': 59.9343, 'lon': 30.3351}
                }
            ],
            'summary': {
                'total_devices': 2,
                'active_devices': 2,
                'avg_battery_level': 83.0,
                'error_count': 1
            },
            'source': 'prosthesis_api',
            'etl_batch': f"telemetry_{datetime.now().strftime('%Y%m%d_%H%M')}"
        }
        
        # Сохраняем телеметрию
        telemetry_path = '/tmp/bionicpro_telemetry_raw.json'
        with open(telemetry_path, 'w') as f:
            json.dump(telemetry_data, f, default=str)
        
        logging.info(f"📊 Телеметрия: {telemetry_data['summary']['total_devices']} устройств, "
                    f"{telemetry_data['summary']['error_count']} ошибок")
        
        return telemetry_path
        
    except Exception as e:
        logging.error(f"❌ Ошибка сбора телеметрии: {e}")
        raise

# ==================== ФУНКЦИИ ЗАГРУЗКИ В CLICKHOUSE ====================
def load_to_clickhouse(**context):
    """Загрузка всех данных в ClickHouse"""
    ti = context['ti']
    crm_path = ti.xcom_pull(task_ids='transform_crm_data')
    telemetry_path = ti.xcom_pull(task_ids='extract_prosthesis_telemetry')
    
    logging.info("💾 [BionicPRO] Загрузка данных в аналитическую БД")
    
    # Имитация подключения для учебных целей
    # В реальности здесь будет реальное подключение к ClickHouse
    client = Client(**CLICKHOUSE_CONFIG) if False else None
    
    # Загружаем данные
    with open(crm_path, 'r') as f:
        crm_data = json.load(f)
    
    with open(telemetry_path, 'r') as f:
        telemetry_data = json.load(f)
    
    # Имитация создания таблиц и вставки данных
    logging.info(f"📋 Созданы таблицы: crm_orders, prosthesis_telemetry")
    logging.info(f"📥 Вставлено: {len(crm_data['orders'])} заказов, "
                f"{len(telemetry_data.get('records', []))} записей телеметрии")
    
    return {
        'orders_count': len(crm_data['orders']),
        'telemetry_count': len(telemetry_data.get('records', [])),
        'timestamp': datetime.now().isoformat(),
        'status': 'success'
    }

# ==================== ФУНКЦИИ ДЛЯ ВИТРИНЫ ОТЧЕТНОСТИ ====================
def refresh_sales_mart(**context):
    """Обновление витрины для отчета по продажам"""
    logging.info("📈 [BionicPRO] Обновление витрины продаж")
    
    # Имитация работы с ClickHouse для учебных целей
    stats = (2, 700000.00, 0.5)  # (orders, revenue, completion_rate)
    
    logging.info(f"✅ Витрина продаж обновлена: {stats[0]} заказов, {stats[1]:.2f} руб.")
    return stats

def refresh_prosthesis_health_mart(**context):
    """Обновление витрины состояния протезов"""
    logging.info("🏥 [BionicPRO] Обновление витрины здоровья протезов")
    
    # Имитация работы с ClickHouse для учебных целей
    stats = {
        'devices_monitored': 2,
        'avg_health_score': 82.5,
        'total_errors': 1,
        'critical_devices': 0
    }
    
    logging.info(f"✅ Витрина здоровья обновлена: {stats['devices_monitored']} устройств, "
                f"средний health score: {stats['avg_health_score']:.1f}")
    
    return stats

def send_daily_report(**context):
    """Отправка ежедневного отчета по email"""
    ti = context['ti']
    sales_stats = ti.xcom_pull(task_ids='refresh_sales_mart')
    health_stats = ti.xcom_pull(task_ids='refresh_prosthesis_health_mart')
    
    # Формируем HTML отчет
    report_date = datetime.now().strftime('%d.%m.%Y')
    
    email_content = f"""
    <html>
    <body>
        <h2>📊 BionicPRO - Ежедневный отчет {report_date}</h2>
        
        <h3>💰 Продажи</h3>
        <ul>
            <li>Всего заказов: {sales_stats[0] if sales_stats else 0}</li>
            <li>Общая выручка: {sales_stats[1]:,.2f if sales_stats else 0} руб.</li>
            <li>Средняя конверсия: {(sales_stats[2]*100 if sales_stats else 0):.1f}%</li>
        </ul>
        
        <h3>🏥 Состояние протезов</h3>
        <ul>
            <li>Мониторится устройств: {health_stats.get('devices_monitored', 0) if health_stats else 0}</li>
            <li>Средний health score: {health_stats.get('avg_health_score', 0):.1f if health_stats else 0}</li>
            <li>Всего ошибок: {health_stats.get('total_errors', 0) if health_stats else 0}</li>
            <li>Критических устройств: {health_stats.get('critical_devices', 0) if health_stats else 0}</li>
        </ul>
        
        <hr>
        <p><small>Отчет сгенерирован автоматически системой BionicPRO Analytics</small></p>
    </body>
    </html>
    """
    
    logging.info(f"📧 Отчет подготовлен для отправки")
    
    # Сохраняем отчет в файл (для учебных целей)
    with open(f'/tmp/bionicpro_report_{report_date}.html', 'w') as f:
        f.write(email_content)
    
    return email_content

# ==================== DAG ОПРЕДЕЛЕНИЯ ====================
default_args = {
    'owner': 'bionicpro_analytics',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['analytics@bionicpro.ru'],
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=10)
}

# DAG 1: Ежедневный сбор данных (запускается в 03:00)
dag_daily_collection = DAG(
    'bionicpro_daily_data_collection',
    default_args=default_args,
    description='Ежедневный сбор данных CRM и телеметрии для BionicPRO',
    schedule_interval='0 3 * * *',  # Каждый день в 03:00 ночи
    catchup=False,
    tags=['bionicpro', 'crm', 'telemetry', 'daily']
)

with dag_daily_collection:
    start_collection = DummyOperator(task_id='start_daily_collection')
    
    extract_crm_task = PythonOperator(
        task_id='extract_crm_data',
        python_callable=extract_crm_data
    )
    
    transform_crm_task = PythonOperator(
        task_id='transform_crm_data',
        python_callable=transform_crm_data
    )
    
    extract_telemetry_task = PythonOperator(
        task_id='extract_prosthesis_telemetry',
        python_callable=extract_prosthesis_telemetry
    )
    
    load_data_task = PythonOperator(
        task_id='load_to_clickhouse',
        python_callable=load_to_clickhouse
    )
    
    end_collection = DummyOperator(task_id='end_daily_collection')
    
    # Порядок: CRM → Трансформация → Параллельно телеметрия → Загрузка
    start_collection >> extract_crm_task >> transform_crm_task >> load_data_task >> end_collection
    start_collection >> extract_telemetry_task >> load_data_task

# DAG 2: Часовое обновление витрин (для мониторинга)
dag_hourly_marts = DAG(
    'bionicpro_hourly_marts_refresh',
    default_args=default_args,
    description='Часовое обновление витрин для мониторинга BionicPRO',
    schedule_interval='0 */1 * * *',  # Каждый час
    catchup=False,
    tags=['bionicpro', 'marts', 'hourly', 'monitoring']
)

with dag_hourly_marts:
    start_marts = DummyOperator(task_id='start_hourly_marts')
    
    refresh_sales_task = PythonOperator(
        task_id='refresh_sales_mart',
        python_callable=refresh_sales_mart
    )
    
    refresh_health_task = PythonOperator(
        task_id='refresh_prosthesis_health_mart',
        python_callable=refresh_prosthesis_health_mart
    )
    
    end_marts = DummyOperator(task_id='end_hourly_marts')
    
    # Параллельное обновление витрин
    start_marts >> [refresh_sales_task, refresh_health_task] >> end_marts

# DAG 3: Ежедневная отчетность (в 09:00)
dag_daily_reporting = DAG(
    'bionicpro_daily_reporting',
    default_args=default_args,
    description='Ежедневная генерация отчетов для руководства BionicPRO',
    schedule_interval='0 9 * * *',  # Каждый день в 09:00 утра
    catchup=False,
    tags=['bionicpro', 'reporting', 'email', 'daily']
)

with dag_daily_reporting:
    start_reporting = DummyOperator(task_id='start_daily_reporting')
    
    generate_report_task = PythonOperator(
        task_id='send_daily_report',
        python_callable=send_daily_report
    )
    
    # EmailOperator требует настройки SMTP, используем PythonOperator для имитации
    email_report_task = PythonOperator(
        task_id='email_daily_report',
        python_callable=lambda: logging.info("📤 Отчет отправлен по email")
    )
    
    end_reporting = DummyOperator(task_id='end_daily_reporting')
    
    start_reporting >> generate_report_task >> email_report_task >> end_reporting

# ==================== ИНФОРМАЦИОННОЕ СООБЩЕНИЕ ====================
if __name__ == "__main__":
    print("""
    ✅ BionicPRO ETL система настроена:

    1. СБОР ДАННЫХ (bionicpro_daily_data_collection):
       - Запуск: Каждый день в 03:00
       - Источники: Битрикс24 CRM + API протезов
       - Результат: Данные в ClickHouse для аналитики

    2. ОБНОВЛЕНИЕ ВИТРИН (bionicpro_hourly_marts_refresh):
       - Запуск: Каждый час
       - Витрины: Продажи + Состояние протезов
       - Для: Мониторинга в реальном времени

    3. ОТЧЕТНОСТЬ (bionicpro_daily_reporting):
       - Запуск: Каждый день в 09:00
       - Получатели: Руководство компании
       - Содержание: Ключевые метрики бизнеса

    👥 Пользователи системы:
    - Руководство BionicPRO - стратегические отчеты
    - Отдел продаж - мониторинг заказов
    - Техподдержка - состояние устройств
    - Производство - статус изготовления
    - Клиенты - отчеты по их протезам
    """)