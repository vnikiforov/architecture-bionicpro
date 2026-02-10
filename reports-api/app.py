from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any, Callable
import re

from config import settings
from api.endpoints import reports
from database.clickhouse_client import get_clickhouse_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

security = HTTPBearer()

class SecurityMiddleware:
    """Middleware для проверки безопасности и изоляции данных"""
    
    @staticmethod
    async def extract_user_id_from_path(request: Request) -> int:
        """Извлечение user_id из пути запроса"""
        # Ищем user_id в пути (например, /api/v1/reports/1001/summary)
        path = request.url.path
        user_id_match = re.search(r'/reports/(\d+)', path)
        
        if user_id_match:
            return int(user_id_match.group(1))
        return None
    
    @staticmethod
    async def verify_user_access(request: Request, auth_data: Dict[str, Any]) -> None:
        """Проверка, что пользователь запрашивает только свои данные"""
        try:
            # Извлекаем user_id из пути
            requested_user_id = await SecurityMiddleware.extract_user_id_from_path(request)
            
            # Для POST запросов user_id может быть в теле
            if request.method == "POST" and not requested_user_id:
                # В реальном проекте нужно парсить тело запроса
                # Для упрощения предположим, что проверка будет в endpoint
                return
            
            # Если user_id найден в пути, проверяем доступ
            if requested_user_id and requested_user_id != auth_data.get('user_id'):
                logger.warning(
                    f"Попытка несанкционированного доступа: "
                    f"пользователь {auth_data.get('user_id')} "
                    f"пытается получить данные пользователя {requested_user_id}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Доступ запрещен. Вы можете запрашивать только свои данные."
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка проверки доступа: {e}")
            raise HTTPException(status_code=500, detail="Ошибка проверки прав доступа")

async def verify_token_and_access(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Проверка токена и прав доступа к данным
    """
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Не предоставлен токен авторизации"
        )
    
    # Извлекаем user_id из токена
    try:
        if token.startswith("user_"):
            user_id = int(token.split("_")[1])
            auth_data = {"user_id": user_id, "token": token}
            
            # Проверяем доступ к запрашиваемым данным
            await SecurityMiddleware.verify_user_access(request, auth_data)
            
            return auth_data
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
    """Контекст жизненного цикла приложения"""
    logger.info("🚀 Запуск BionicPRO Reports API (обновленная версия с изоляцией)")
    
    try:
        client = get_clickhouse_client()
        client.execute("SELECT 1")
        logger.info("✅ Подключение к ClickHouse установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к ClickHouse: {e}")
        raise
    
    yield
    
    logger.info("🛑 Остановка BionicPRO Reports API")

app = FastAPI(
    title="BionicPRO Reports API",
    description="API для получения отчетов по бионическим протезам с строгой изоляцией данных",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров с зависимостью проверки доступа
app.include_router(
    reports.router,
    prefix="/api/v1",
    tags=["reports"],
    dependencies=[Depends(verify_token_and_access)]
)

@app.get("/")
async def root():
    return {
        "service": "BionicPRO Reports API v2.0",
        "version": "2.0.0",
        "description": "API с строгой изоляцией данных пользователей"
    }

@app.get("/health")
async def health_check():
    try:
        client = get_clickhouse_client()
        result = client.execute("SELECT 1 as status")
        
        return {
            "status": "healthy",
            "database": "connected" if result else "disconnected",
            "security": "strict_isolation_enabled",
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