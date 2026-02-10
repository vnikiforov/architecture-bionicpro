from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from config import settings
from api.endpoints import reports
from database.clickhouse_client import get_clickhouse_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Безопасность
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    Простая проверка токена (в реальном проекте нужно использовать JWT)
    В учебных целях проверяем, что токен не пустой
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Не предоставлен токен авторизации"
        )
    
    # В реальном проекте здесь должна быть проверка JWT токена
    # через Keycloak или другую IdP систему
    
    # Для учебных целей просто извлекаем user_id из токена
    # В реальности user_id должен быть внутри JWT payload
    try:
        # Имитация: токен в формате "user_{user_id}"
        if token.startswith("user_"):
            user_id = int(token.split("_")[1])
            return {"user_id": user_id, "token": token}
        else:
            raise HTTPException(
                status_code=401,
                detail="Неверный формат токена"
            )
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=401,
            detail="Неверный токен авторизации"
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекст жизненного цикла приложения
    """
    # Инициализация при запуске
    logger.info("🚀 Запуск BionicPRO Reports API")
    
    # Проверка подключения к ClickHouse
    try:
        client = get_clickhouse_client()
        # Простой запрос для проверки соединения
        client.execute("SELECT 1")
        logger.info("✅ Подключение к ClickHouse установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к ClickHouse: {e}")
        raise
    
    yield
    
    # Очистка при остановке
    logger.info("🛑 Остановка BionicPRO Reports API")

# Создание приложения
app = FastAPI(
    title="BionicPRO Reports API",
    description="API для получения отчетов по бионическим протезам",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(
    reports.router,
    prefix="/api/v1",
    tags=["reports"],
    dependencies=[Depends(verify_token)]
)

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "BionicPRO Reports API",
        "version": "1.0.0",
        "description": "API для отчетов по бионическим протезам"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        client = get_clickhouse_client()
        # Проверяем подключение к ClickHouse
        result = client.execute("SELECT 1 as status")
        
        return {
            "status": "healthy",
            "database": "connected" if result else "disconnected",
            "timestamp": "2024-03-15T10:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ошибка подключения к БД: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )