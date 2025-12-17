"""
Pydantic схемы для валидации данных
"""
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# === Енумы ===

class BookFormat(str, Enum):
    PAPER = "paper"
    EBOOK = "ebook"
    AUDIOBOOK = "audiobook"


class BookStatus(str, Enum):
    PLANNED = "planned"
    READING = "reading"
    FINISHED = "finished"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    WISHLIST = "wishlist"


# === Авторы ===

class AuthorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class AuthorCreate(AuthorBase):
    pass


class AuthorResponse(AuthorBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# === Жанры ===

class GenreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GenreCreate(GenreBase):
    pass


class GenreResponse(GenreBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# === Книги ===

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: str | None = None
    description: str | None = None
    language: str = "ru"
    format: BookFormat = BookFormat.PAPER
    status: BookStatus = BookStatus.PLANNED
    total_pages: int | None = None
    current_page: int = 0
    started_at: date | None = None
    finished_at: date | None = None
    published_year: int | None = None
    rating: int | None = Field(None, ge=1, le=10)
    notes: str | None = None
    quotes: list[str] = []
    location: str | None = None
    cover_url: str | None = None
    isbn: str | None = None


class BookCreate(BookBase):
    """Схема для создания книги"""
    authors: list[str] = []  # Имена авторов (создадутся автоматически)
    genres: list[str] = []   # Названия жанров (создадутся автоматически)
    auto_fetch_cover: bool = True  # Автоматически искать обложку


class BookUpdate(BaseModel):
    """Схема для обновления книги (все поля опциональны)"""
    title: str | None = Field(None, min_length=1, max_length=500)
    subtitle: str | None = None
    description: str | None = None
    language: str | None = None
    format: BookFormat | None = None
    status: BookStatus | None = None
    total_pages: int | None = None
    current_page: int | None = None
    started_at: date | None = None
    finished_at: date | None = None
    published_year: int | None = None
    rating: int | None = Field(None, ge=1, le=10)
    notes: str | None = None
    quotes: list[str] | None = None
    location: str | None = None
    cover_url: str | None = None
    isbn: str | None = None
    authors: list[str] | None = None
    genres: list[str] | None = None


class BookResponse(BookBase):
    """Схема ответа с книгой"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    authors: list[AuthorResponse] = []
    genres: list[GenreResponse] = []
    progress: float = 0.0


class BookListResponse(BaseModel):
    """Ответ со списком книг"""
    items: list[BookResponse]
    total: int
    page: int = 1
    per_page: int = 20


# === Статистика ===

class ReadingStats(BaseModel):
    """Статистика чтения"""
    total_books: int = 0
    books_finished: int = 0
    books_reading: int = 0
    books_planned: int = 0
    pages_read_total: int = 0
    average_rating: float | None = None


class MonthlyStats(BaseModel):
    """Статистика по месяцам"""
    month: str  # "2024-01"
    books_finished: int = 0
    pages_read: int = 0


class YearlyStats(BaseModel):
    """Годовая статистика"""
    year: int
    books_finished: int = 0
    pages_read: int = 0
    monthly: list[MonthlyStats] = []


class TopAuthor(BaseModel):
    """Топ-автор"""
    name: str
    books_count: int
    average_rating: float | None = None


class TopGenre(BaseModel):
    """Топ-жанр"""
    name: str
    books_count: int


class FullStats(BaseModel):
    """Полная статистика"""
    overview: ReadingStats
    current_year: YearlyStats | None = None
    top_authors: list[TopAuthor] = []
    top_genres: list[TopGenre] = []


# === Импорт/Экспорт ===

class ImportResult(BaseModel):
    """Результат импорта"""
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = []


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


# === Поиск обложки ===

class CoverSearchResult(BaseModel):
    """Результат поиска обложки"""
    cover_url: str | None = None
    description: str | None = None
    published_year: int | None = None
    external_id: str | None = None
    source: str = "unknown"  # google_books, open_library
