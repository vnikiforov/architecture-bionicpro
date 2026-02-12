FROM apache/airflow:2.7.0-python3.10

USER root

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        wget \
        curl \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

USER airflow

# Копируем requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт инициализации
COPY scripts/setup-connections.py /opt/airflow/setup-connections.py