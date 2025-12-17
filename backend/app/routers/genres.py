"""
Роутер для работы с жанрами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ..db import get_db
from ..models import Genre, book_genres
from ..schemas import GenreResponse, GenreCreate

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("", response_model=list[GenreResponse])
def get_genres(
    search: Optional[str] = Query(None, description="Поиск по названию"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Получить список жанров"""
    query = db.query(Genre)
    
    if search:
        query = query.filter(Genre.name.ilike(f"%{search}%"))
    
    query = query.order_by(Genre.name)
    return query.limit(limit).all()


@router.get("/popular", response_model=list[dict])
def get_popular_genres(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Получить популярные жанры (по количеству книг)"""
    results = (
        db.query(Genre, func.count(book_genres.c.book_id).label("books_count"))
        .join(book_genres)
        .group_by(Genre.id)
        .order_by(func.count(book_genres.c.book_id).desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": genre.id,
            "name": genre.name,
            "books_count": count
        }
        for genre, count in results
    ]


@router.get("/{genre_id}", response_model=GenreResponse)
def get_genre(genre_id: int, db: Session = Depends(get_db)):
    """Получить жанр по ID"""
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Жанр не найден")
    return genre


@router.post("", response_model=GenreResponse, status_code=201)
def create_genre(
    genre_data: GenreCreate,
    db: Session = Depends(get_db)
):
    """Создать новый жанр"""
    existing = db.query(Genre).filter(Genre.name == genre_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Жанр уже существует")
    
    genre = Genre(name=genre_data.name)
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre


@router.delete("/{genre_id}", status_code=204)
def delete_genre(genre_id: int, db: Session = Depends(get_db)):
    """Удалить жанр"""
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Жанр не найден")
    
    db.delete(genre)
    db.commit()
    return None
