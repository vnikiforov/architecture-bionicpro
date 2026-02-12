-- Инициализация аналитической базы BionicPRO
CREATE DATABASE IF NOT EXISTS bionicpro_analytics;

-- 1. Таблица для CRM данных (заказы, клиенты, производство)
CREATE TABLE IF NOT EXISTS bionicpro_analytics.crm_orders (
    order_id UInt64,
    order_title String,
    stage_id String,
    amount Decimal(10,2),
    order_date Date,
    contact_id UInt64,
    assigned_to UInt64,
    prosthesis_model String,
    prosthesis_category String,
    region String,
    load_timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (order_date, region, prosthesis_category);

-- 2. Таблица телеметрии протезов
CREATE TABLE IF NOT EXISTS bionicpro_analytics.prosthesis_telemetry (
    device_id String,
    patient_id UInt64,
    measurement_time DateTime,
    battery_level Float32,
    usage_hours Float32,
    motor_temperature Float32,
    sensor_readings String,
    error_codes Array(UInt16),
    firmware_version String,
    location_lat Float64,
    location_lon Float64,
    load_timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (measurement_time, device_id);

-- 3. Витрина продаж для отчетов
CREATE TABLE IF NOT EXISTS bionicpro_analytics.sales_mart (
    report_date Date,
    region String,
    prosthesis_model String,
    prosthesis_category String,
    orders_count UInt32,
    total_revenue Decimal(15,2),
    avg_order_amount Decimal(10,2),
    unique_customers UInt32,
    completion_rate Float32,
    load_timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (report_date, region, prosthesis_category);

-- 4. Витрина технического состояния протезов
CREATE TABLE IF NOT EXISTS bionicpro_analytics.prosthesis_health_mart (
    report_date Date,
    device_id String,
    avg_battery_level Float32,
    total_usage_hours Float32,
    avg_motor_temp Float32,
    error_count UInt32,
    firmware_version String,
    days_active UInt32,
    last_measurement DateTime,
    health_score Float32,
    load_timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (report_date, device_id);

-- 5. Создаем пользователей с разными правами
CREATE USER IF NOT EXISTS etl_user IDENTIFIED WITH sha256_password BY 'etl_bionicpro_2024';
CREATE USER IF NOT EXISTS report_user IDENTIFIED WITH sha256_password BY 'report_bionicpro_2024';
CREATE USER IF NOT EXISTS readonly_user IDENTIFIED WITH sha256_password BY 'readonly_bionicpro_2024';

-- Права для ETL процесса
GRANT INSERT, SELECT ON bionicpro_analytics.* TO etl_user;

-- Права для Report Service (только витрины)
GRANT SELECT ON bionicpro_analytics.sales_mart TO report_user;
GRANT SELECT ON bionicpro_analytics.prosthesis_health_mart TO report_user;

-- Права только на чтение для аналитиков
GRANT SELECT ON bionicpro_analytics.* TO readonly_user;

-- 6. Тестовые данные для демонстрации
INSERT INTO bionicpro_analytics.crm_orders 
(order_id, order_title, stage_id, amount, order_date, prosthesis_model, prosthesis_category, region) VALUES
(1001, 'Заказ протеза BionicPRO V2', 'WON', 250000.00, '2024-03-01', 'BIONICPRO_V2', 'Стандарт', 'Москва'),
(1002, 'Кастомный протез для спортсмена', 'MANUFACTURING', 450000.00, '2024-03-05', 'BIONICPRO_CUSTOM', 'Кастомный', 'Санкт-Петербург'),
(1003, 'Протез BionicPRO V1 для ребенка', 'PREPARATION', 180000.00, '2024-03-10', 'BIONICPRO_V1', 'Начальный', 'Новосибирск');

INSERT INTO bionicpro_analytics.prosthesis_telemetry 
(device_id, patient_id, measurement_time, battery_level, usage_hours, motor_temperature, firmware_version) VALUES
('BP-2024-001', 1001, '2024-03-15 08:30:00', 85.5, 24.3, 32.1, '2.1.4'),
('BP-2024-001', 1001, '2024-03-15 12:45:00', 72.3, 25.1, 35.2, '2.1.4'),
('BP-2024-002', 1002, '2024-03-15 09:15:00', 91.2, 8.5, 28.7, '2.2.0');

-- 7. Создаем материализованное представление для часто запрашиваемых метрик
CREATE MATERIALIZED VIEW IF NOT EXISTS bionicpro_analytics.daily_sales_summary
ENGINE = SummingMergeTree()
ORDER BY (report_date, region)
AS 
SELECT 
    toDate(order_date) as report_date,
    region,
    count() as daily_orders,
    sum(amount) as daily_revenue,
    avg(amount) as avg_order_value
FROM bionicpro_analytics.crm_orders
GROUP BY report_date, region;

-- 8. Информационное сообщение
SELECT '✅ Аналитическая БД BionicPRO инициализирована' as message;
SELECT '   База: bionicpro_analytics' as db_info;
SELECT '   Таблицы: crm_orders, prosthesis_telemetry, sales_mart, prosthesis_health_mart' as tables;
SELECT format('   Тестовых заказов: {}', count()) as test_orders FROM bionicpro_analytics.crm_orders;
SELECT format('   Тестовых записей телеметрии: {}', count()) as test_telemetry FROM bionicpro_analytics.prosthesis_telemetry;