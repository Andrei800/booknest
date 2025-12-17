"""
Роутеры API BookNest
"""
from .books import router as books_router
from .authors import router as authors_router
from .genres import router as genres_router
from .stats import router as stats_router
from .import_export import router as import_export_router

__all__ = [
    "books_router",
    "authors_router", 
    "genres_router",
    "stats_router",
    "import_export_router"
]
