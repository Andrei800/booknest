"""
Роутер для статистики чтения
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
from typing import Optional

from ..db import get_db
from ..models import Book, Author, Genre, book_authors, book_genres
from ..schemas import (
    ReadingStats, YearlyStats, MonthlyStats, 
    TopAuthor, TopGenre, FullStats, BookStatus
)

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    """Общая статистика по книгам"""
    try:
        total = db.query(Book).count()
        finished = db.query(Book).filter(Book.status == "finished").count()
        reading = db.query(Book).filter(Book.status == "reading").count()
        planned = db.query(Book).filter(Book.status == "planned").count()
        wishlist = db.query(Book).filter(Book.status == "wishlist").count()
        
        # Прочитано страниц
        pages_result = db.query(func.sum(Book.current_page)).scalar()
        pages_read = pages_result or 0
        
        # Средний рейтинг
        avg_rating = db.query(func.avg(Book.rating)).filter(Book.rating.isnot(None)).scalar()
        
        return {
            "total_books": total,
            "books_finished": finished,
            "books_reading": reading,
            "books_planned": planned,
            "books_wishlist": wishlist,
            "pages_read_total": pages_read,
            "average_rating": round(float(avg_rating), 1) if avg_rating else None
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_books": 0,
            "books_finished": 0,
            "books_reading": 0,
            "books_planned": 0,
            "books_wishlist": 0,
            "pages_read_total": 0,
            "average_rating": None
        }


@router.get("/yearly/{year}")
def get_yearly_stats(
    year: int,
    db: Session = Depends(get_db)
):
    """Статистика за год"""
    try:
        # Книги, завершённые в этом году
        finished_query = db.query(Book).filter(
            Book.status == "finished",
            extract('year', Book.finished_at) == year
        )
        
        books_finished = finished_query.count()
        
        # Страницы прочитанных книг
        pages_result = finished_query.with_entities(func.sum(Book.total_pages)).scalar()
        pages_read = pages_result or 0
        
        # Статистика по месяцам
        monthly_stats = []
        for month in range(1, 13):
            month_finished = db.query(Book).filter(
                Book.status == "finished",
                extract('year', Book.finished_at) == year,
                extract('month', Book.finished_at) == month
            ).count()
            
            month_pages = db.query(func.sum(Book.total_pages)).filter(
                Book.status == "finished",
                extract('year', Book.finished_at) == year,
                extract('month', Book.finished_at) == month
            ).scalar() or 0
            
            monthly_stats.append({
                "month": f"{year}-{month:02d}",
                "books_finished": month_finished,
                "pages_read": month_pages
            })
        
        return {
            "year": year,
            "books_finished": books_finished,
            "pages_read": pages_read,
            "monthly": monthly_stats
        }
    except Exception as e:
        print(f"Yearly stats error: {e}")
        return {
            "year": year,
            "books_finished": 0,
            "pages_read": 0,
            "monthly": []
        }


@router.get("/top-authors")
def get_top_authors(
    limit: int = Query(10, ge=1, le=50),
    finished_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Топ авторов по количеству книг"""
    try:
        query = db.query(
            Author.name,
            func.count(book_authors.c.book_id).label("books_count"),
            func.avg(Book.rating).label("avg_rating")
        ).select_from(Author).join(
            book_authors, Author.id == book_authors.c.author_id
        ).join(
            Book, Book.id == book_authors.c.book_id
        )
        
        if finished_only:
            query = query.filter(Book.status == "finished")
        
        results = (
            query
            .group_by(Author.id, Author.name)
            .order_by(func.count(book_authors.c.book_id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "name": name,
                "books_count": count,
                "average_rating": round(float(avg), 1) if avg else None
            }
            for name, count, avg in results
        ]
    except Exception as e:
        print(f"Top authors error: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/top-genres")
def get_top_genres(
    limit: int = Query(10, ge=1, le=50),
    finished_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Топ жанров по количеству книг"""
    try:
        query = db.query(
            Genre.name,
            func.count(book_genres.c.book_id).label("books_count")
        ).select_from(Genre).join(
            book_genres, Genre.id == book_genres.c.genre_id
        ).join(
            Book, Book.id == book_genres.c.book_id
        )
        
        if finished_only:
            query = query.filter(Book.status == "finished")
        
        results = (
            query
            .group_by(Genre.id, Genre.name)
            .order_by(func.count(book_genres.c.book_id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            {"name": name, "books_count": count}
            for name, count in results
        ]
    except Exception as e:
        print(f"Top genres error: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/full")
def get_full_stats(db: Session = Depends(get_db)):
    """Полная статистика"""
    try:
        # Обзор
        overview = get_overview_stats(db)
        
        # Текущий год
        current_year = datetime.now().year
        yearly = get_yearly_stats(current_year, db)
        
        # Топ авторов и жанров
        top_authors = get_top_authors(limit=5, finished_only=False, db=db)
        top_genres = get_top_genres(limit=5, finished_only=False, db=db)
        
        return {
            "overview": overview,
            "current_year": yearly,
            "top_authors": top_authors,
            "top_genres": top_genres
        }
    except Exception as e:
        print(f"Full stats error: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем минимальную статистику
        return {
            "overview": {
                "total_books": 0,
                "books_finished": 0,
                "books_reading": 0,
                "books_planned": 0,
                "pages_read_total": 0,
                "average_rating": None
            },
            "current_year": None,
            "top_authors": [],
            "top_genres": []
        }


@router.get("/reading-challenge")
def get_reading_challenge(
    year: int = Query(default_factory=lambda: datetime.now().year),
    goal: int = Query(12, description="Цель на год (книг)"),
    db: Session = Depends(get_db)
):
    """Прогресс челленджа чтения"""
    finished = db.query(Book).filter(
        Book.status == BookStatus.FINISHED.value,
        extract('year', Book.finished_at) == year
    ).count()
    
    progress = round(finished / goal * 100, 1) if goal > 0 else 0
    remaining = max(0, goal - finished)
    
    # Сколько месяцев осталось
    current_month = datetime.now().month
    months_left = 12 - current_month + 1
    books_per_month = round(remaining / months_left, 1) if months_left > 0 else 0
    
    return {
        "year": year,
        "goal": goal,
        "finished": finished,
        "remaining": remaining,
        "progress_percent": progress,
        "on_track": finished >= (goal * current_month / 12),
        "books_per_month_needed": books_per_month
    }
