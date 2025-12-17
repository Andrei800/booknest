"""
Роутер для работы с книгами
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional

from ..db import get_db
from ..models import Book, Author, Genre
from ..schemas import (
    BookCreate, BookUpdate, BookResponse, BookListResponse,
    BookStatus, BookFormat
)
from ..services.covers import fetch_book_metadata, search_multiple_covers, search_by_isbn

router = APIRouter(prefix="/books", tags=["books"])


def get_or_create_author(db: Session, name: str) -> Author:
    """Получить или создать автора"""
    author = db.query(Author).filter(Author.name == name).first()
    if not author:
        author = Author(name=name)
        db.add(author)
        db.flush()
    return author


def get_or_create_genre(db: Session, name: str) -> Genre:
    """Получить или создать жанр"""
    genre = db.query(Genre).filter(Genre.name == name).first()
    if not genre:
        genre = Genre(name=name)
        db.add(genre)
        db.flush()
    return genre


async def fetch_and_update_cover(book_id: int, title: str, author: str | None):
    """Фоновая задача для поиска обложки"""
    from ..db import SessionLocal
    
    metadata = await fetch_book_metadata(title, author)
    if metadata:
        db = SessionLocal()
        try:
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                if metadata.cover_url and not book.cover_url:
                    book.cover_url = metadata.cover_url
                if metadata.description and not book.description:
                    book.description = metadata.description
                if metadata.published_year and not book.published_year:
                    book.published_year = metadata.published_year
                if metadata.external_id and not book.external_id:
                    book.external_id = metadata.external_id
                db.commit()
        finally:
            db.close()


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(
    book_data: BookCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Создать новую книгу"""
    # Создаём книгу
    book = Book(
        title=book_data.title,
        subtitle=book_data.subtitle,
        description=book_data.description,
        language=book_data.language,
        format=book_data.format.value,
        status=book_data.status.value,
        total_pages=book_data.total_pages,
        current_page=book_data.current_page,
        started_at=book_data.started_at,
        finished_at=book_data.finished_at,
        published_year=book_data.published_year,
        rating=book_data.rating,
        notes=book_data.notes,
        quotes=book_data.quotes,
        location=book_data.location,
        cover_url=book_data.cover_url,
        isbn=book_data.isbn,
    )
    
    # Добавляем авторов
    for author_name in book_data.authors:
        author = get_or_create_author(db, author_name.strip())
        book.authors.append(author)
    
    # Добавляем жанры
    for genre_name in book_data.genres:
        genre = get_or_create_genre(db, genre_name.strip())
        book.genres.append(genre)
    
    db.add(book)
    db.commit()
    db.refresh(book)
    
    # Запускаем фоновый поиск обложки
    if book_data.auto_fetch_cover and not book_data.cover_url:
        first_author = book_data.authors[0] if book_data.authors else None
        background_tasks.add_task(fetch_and_update_cover, book.id, book.title, first_author)
    
    return book


@router.get("/isbn/{isbn}")
async def get_book_by_isbn(isbn: str):
    """Поиск информации о книге по ISBN"""
    result = await search_by_isbn(isbn)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Книга с ISBN {isbn} не найдена"
        )
    
    return result


@router.get("", response_model=BookListResponse)
def get_books(
    search: Optional[str] = Query(None, description="Поиск по названию/автору"),
    status: Optional[BookStatus] = Query(None, description="Фильтр по статусу"),
    format: Optional[BookFormat] = Query(None, description="Фильтр по формату"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    genre: Optional[str] = Query(None, description="Фильтр по жанру"),
    language: Optional[str] = Query(None, description="Фильтр по языку"),
    min_rating: Optional[int] = Query(None, ge=1, le=10, description="Минимальный рейтинг"),
    year: Optional[int] = Query(None, description="Год публикации"),
    sort_by: str = Query("created_at", description="Сортировка: created_at, title, rating, finished_at"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить список книг с фильтрами"""
    query = db.query(Book)
    
    # Поиск
    if search:
        search_term = f"%{search}%"
        query = query.outerjoin(Book.authors).filter(
            or_(
                Book.title.ilike(search_term),
                Author.name.ilike(search_term)
            )
        ).distinct()
    
    # Фильтры
    if status:
        query = query.filter(Book.status == status.value)
    if format:
        query = query.filter(Book.format == format.value)
    if language:
        query = query.filter(Book.language == language)
    if min_rating:
        query = query.filter(Book.rating >= min_rating)
    if year:
        query = query.filter(Book.published_year == year)
    
    # Фильтр по автору
    if author:
        query = query.join(Book.authors).filter(Author.name.ilike(f"%{author}%"))
    
    # Фильтр по жанру
    if genre:
        query = query.join(Book.genres).filter(Genre.name.ilike(f"%{genre}%"))
    
    # Подсчёт общего количества
    total = query.count()
    
    # Сортировка
    sort_column = getattr(Book, sort_by, Book.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Пагинация
    offset = (page - 1) * per_page
    books = query.offset(offset).limit(per_page).all()
    
    return BookListResponse(
        items=books,
        total=total,
        page=page,
        per_page=per_page
    )


# ВАЖНО: Этот роут должен быть ДО /{book_id}, иначе "search" интерпретируется как book_id
@router.get("/search/covers")
async def search_covers_by_query(
    title: str = Query(..., description="Название книги"),
    author: str = Query(None, description="Автор книги")
):
    """Поиск обложек по названию и автору"""
    covers_data = await search_multiple_covers(title, author)
    # Возвращаем просто массив URL
    return [cover['url'] for cover in covers_data]


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Получить книгу по ID"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book


@router.patch("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Session = Depends(get_db)
):
    """Обновить книгу"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    # Обновляем простые поля
    update_data = book_data.model_dump(exclude_unset=True, exclude={"authors", "genres"})
    for field, value in update_data.items():
        if field in ("status", "format") and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(book, field, value)
    
    # Обновляем авторов
    if book_data.authors is not None:
        book.authors = []
        for author_name in book_data.authors:
            author = get_or_create_author(db, author_name.strip())
            book.authors.append(author)
    
    # Обновляем жанры
    if book_data.genres is not None:
        book.genres = []
        for genre_name in book_data.genres:
            genre = get_or_create_genre(db, genre_name.strip())
            book.genres.append(genre)
    
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Удалить книгу"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    db.delete(book)
    db.commit()
    return None


@router.post("/{book_id}/start-reading", response_model=BookResponse)
def start_reading(book_id: int, db: Session = Depends(get_db)):
    """Начать читать книгу"""
    from datetime import date
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    book.status = BookStatus.READING.value
    if not book.started_at:
        book.started_at = date.today()
    
    db.commit()
    db.refresh(book)
    return book


@router.post("/{book_id}/finish-reading", response_model=BookResponse)
def finish_reading(
    book_id: int,
    rating: Optional[int] = Query(None, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Завершить чтение книги"""
    from datetime import date
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    book.status = BookStatus.FINISHED.value
    book.finished_at = date.today()
    if book.total_pages:
        book.current_page = book.total_pages
    if rating:
        book.rating = rating
    
    db.commit()
    db.refresh(book)
    return book


@router.post("/{book_id}/update-progress", response_model=BookResponse)
def update_progress(
    book_id: int,
    current_page: int = Query(..., ge=0),
    db: Session = Depends(get_db)
):
    """Обновить прогресс чтения"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    book.current_page = current_page
    
    # Автоматически меняем статус
    if book.status == BookStatus.PLANNED.value and current_page > 0:
        book.status = BookStatus.READING.value
        if not book.started_at:
            from datetime import date
            book.started_at = date.today()
    
    # Если дочитали до конца
    if book.total_pages and current_page >= book.total_pages:
        book.status = BookStatus.FINISHED.value
        if not book.finished_at:
            from datetime import date
            book.finished_at = date.today()
    
    db.commit()
    db.refresh(book)
    return book


@router.get("/{book_id}/covers")
async def search_covers_for_book(book_id: int, db: Session = Depends(get_db)):
    """Поиск вариантов обложек для книги"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    first_author = book.authors[0].name if book.authors else None
    covers = await search_multiple_covers(book.title, first_author)
    
    return {"covers": covers, "current_cover": book.cover_url}


@router.patch("/{book_id}/cover")
async def update_book_cover(
    book_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    """Обновить обложку книги"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    cover_url = data.get("cover_url")
    if not cover_url:
        raise HTTPException(status_code=400, detail="URL обложки не указан")
    
    book.cover_url = cover_url
    db.commit()
    db.refresh(book)
    return {"success": True, "cover_url": book.cover_url}
