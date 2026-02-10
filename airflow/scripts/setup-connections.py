#!/usr/bin/env python3
"""
Скрипт для автоматической настройки Airflow Connections
"""

import os
import json
from airflow.models import Connection
from airflow import settings

def setup_connections():
    """Настраивает все необходимые connections"""
    
    connections = [
        {
            'conn_id': 'clickhouse_olap',
            'conn_type': 'clickhouse',
            'host': 'clickhouse',
            'port': 8123,
            'schema': 'analytics',
            'login': 'admin',
            'password': 'admin123',
            'extra': json.dumps({
                'secure': False,
                'verify': False
            })
        },
        {
            'conn_id': 'crm_api',
            'conn_type': 'http',
            'host': 'http://mock-crm-api:1080',
            'port': 1080,
            'login': '',
            'password': 'test_token',
            'extra': json.dumps({
                'headers': {
                    'Authorization': 'Bearer test_token',
                    'Content-Type': 'application/json'
                }
            })
        }
    ]
    
    session = settings.Session()
    
    for conn_data in connections:
        conn_id = conn_data['conn_id']
        
        # Проверяем, существует ли connection
        existing = session.query(Connection).filter(Connection.conn_id == conn_id).first()
        
        if existing:
            print(f"⚠️  Connection {conn_id} уже существует, обновляю...")
            for key, value in conn_data.items():
                setattr(existing, key, value)
        else:
            print(f"✅ Создаю connection: {conn_id}")
            conn = Connection(**conn_data)
            session.add(conn)
    
    session.commit()
    session.close()
    print("🎉 Все connections настроены!")

if __name__ == "__main__":
    setup_connections()