"""
BookNest - Главный файл приложения FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from .config import get_settings
from .db import init_db
from .routers import (
    books_router,
    authors_router,
    genres_router,
    stats_router,
    import_export_router
)
from .routers.ai import router as ai_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle события приложения"""
    # Startup
    init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} запущен!")
    yield
    # Shutdown
    print("👋 Приложение остановлено")


# Создаём приложение
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    📚 **BookNest** — приложение для ведения читательского дневника с AI-функциями.
    
    ## Возможности
    
    * 📖 Каталогизация книг (бумажных, электронных, аудио)
    * 📊 Отслеживание прогресса чтения
    * 🔍 Поиск и фильтрация по авторам, жанрам, статусу
    * 📈 Статистика чтения за год/месяц
    * 🤖 Автоматический поиск обложек и описаний
    * 📥 Импорт/экспорт в CSV и JSON
    """,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры API
app.include_router(books_router, prefix="/api")
app.include_router(authors_router, prefix="/api")
app.include_router(genres_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(import_export_router, prefix="/api")
app.include_router(ai_router, prefix="/api")


# Статические файлы фронтенда
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Главная страница — отдаём фронтенд"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api"
    }


@app.get("/api")
async def api_info():
    """Информация об API"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "books": "/api/books",
            "authors": "/api/authors",
            "genres": "/api/genres",
            "stats": "/api/stats",
            "import_export": "/api/import-export"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "healthy", "app": settings.APP_NAME}
