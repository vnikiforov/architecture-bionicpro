from typing import Optional
from clickhouse_driver import Client
import logging
from config import settings

logger = logging.getLogger(__name__)

class ClickHouseClient:
    """Клиент для работы с ClickHouse"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Получение подключения к ClickHouse (синглтон)"""
        if cls._instance is None:
            try:
                cls._instance = Client(
                    host=settings.CLICKHOUSE_HOST,
                    port=settings.CLICKHOUSE_PORT,
                    user=settings.CLICKHOUSE_USER,
                    password=settings.CLICKHOUSE_PASSWORD,
                    database=settings.CLICKHOUSE_DATABASE,
                    settings={'connect_timeout': 10, 'receive_timeout': 30}
                )
                logger.info(f"Подключение к ClickHouse: {settings.CLICKHOUSE_HOST}")
            except Exception as e:
                logger.error(f"Ошибка подключения к ClickHouse: {e}")
                raise
        
        return cls._instance
    
    @classmethod
    def test_connection(cls) -> bool:
        """Тестирование подключения"""
        try:
            client = cls.get_client()
            result = client.execute("SELECT 1")
            return bool(result)
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения: {e}")
            return False

def get_clickhouse_client() -> Client:
    """Функция для dependency injection"""
    return ClickHouseClient.get_client()