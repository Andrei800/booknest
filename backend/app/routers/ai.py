"""
AI Recommendations Router
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from ..db import get_db
from ..models import Book
from ..services.ai_recommendations import get_book_recommendations, get_reading_insights

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/recommendations/{book_id}")
async def get_recommendations_for_book(book_id: int, db: Session = Depends(get_db)):
    """Получить AI-рекомендации похожих книг"""
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    # Собираем данные о книге
    authors = [a.name for a in book.authors]
    genres = [g.name for g in book.genres]
    
    result = await get_book_recommendations(
        title=book.title,
        authors=authors,
        genres=genres,
        notes=book.notes,
        language=book.language or "ru"
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/insights")
async def get_library_insights(db: Session = Depends(get_db)):
    """Получить AI-анализ читательских предпочтений"""
    
    books = db.query(Book).all()
    
    if not books:
        raise HTTPException(status_code=400, detail="Библиотека пуста")
    
    # Преобразуем книги в словари
    books_data = []
    for book in books:
        books_data.append({
            "title": book.title,
            "authors": [{"name": a.name} for a in book.authors],
            "genres": [{"name": g.name} for g in book.genres],
            "rating": book.rating,
            "status": book.status.value if book.status else None
        })
    
    result = await get_reading_insights(books_data)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
