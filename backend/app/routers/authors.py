"""
Роутер для работы с авторами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ..db import get_db
from ..models import Author, Book, book_authors
from ..schemas import AuthorResponse, AuthorCreate

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=list[AuthorResponse])
def get_authors(
    search: Optional[str] = Query(None, description="Поиск по имени"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Получить список авторов"""
    query = db.query(Author)
    
    if search:
        query = query.filter(Author.name.ilike(f"%{search}%"))
    
    query = query.order_by(Author.name)
    return query.limit(limit).all()


@router.get("/popular", response_model=list[dict])
def get_popular_authors(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Получить популярных авторов (по количеству книг)"""
    results = (
        db.query(Author, func.count(book_authors.c.book_id).label("books_count"))
        .join(book_authors)
        .group_by(Author.id)
        .order_by(func.count(book_authors.c.book_id).desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": author.id,
            "name": author.name,
            "books_count": count
        }
        for author, count in results
    ]


@router.get("/{author_id}", response_model=AuthorResponse)
def get_author(author_id: int, db: Session = Depends(get_db)):
    """Получить автора по ID"""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автор не найден")
    return author


@router.get("/{author_id}/books")
def get_author_books(
    author_id: int,
    db: Session = Depends(get_db)
):
    """Получить книги автора"""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автор не найден")
    
    return {
        "author": author,
        "books": author.books
    }


@router.post("", response_model=AuthorResponse, status_code=201)
def create_author(
    author_data: AuthorCreate,
    db: Session = Depends(get_db)
):
    """Создать нового автора"""
    # Проверяем, существует ли уже
    existing = db.query(Author).filter(Author.name == author_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Автор уже существует")
    
    author = Author(name=author_data.name)
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=204)
def delete_author(author_id: int, db: Session = Depends(get_db)):
    """Удалить автора"""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автор не найден")
    
    db.delete(author)
    db.commit()
    return None
