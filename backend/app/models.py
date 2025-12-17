"""
SQLAlchemy модели для BookNest
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, 
    ForeignKey, Table, JSON, Float
)
from sqlalchemy.orm import relationship

from .db import Base


# Many-to-Many: книги <-> авторы
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
)

# Many-to-Many: книги <-> жанры
book_genres = Table(
    "book_genres",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
)


class Author(Base):
    """Модель автора"""
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    
    # Связь с книгами
    books = relationship("Book", secondary=book_authors, back_populates="authors")
    
    def __repr__(self):
        return f"<Author(id={self.id}, name='{self.name}')>"


class Genre(Base):
    """Модель жанра"""
    __tablename__ = "genres"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Связь с книгами
    books = relationship("Book", secondary=book_genres, back_populates="genres")
    
    def __repr__(self):
        return f"<Genre(id={self.id}, name='{self.name}')>"


class Book(Base):
    """Основная модель книги"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    title = Column(String(500), nullable=False, index=True)
    subtitle = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(50), default="ru")
    
    # Формат и статус
    format = Column(String(50), default="paper")  # paper, ebook, audiobook
    status = Column(String(50), default="planned")  # planned, reading, finished, on_hold, dropped
    
    # Прогресс чтения
    total_pages = Column(Integer, nullable=True)
    current_page = Column(Integer, default=0)
    
    # Даты
    started_at = Column(Date, nullable=True)
    finished_at = Column(Date, nullable=True)
    published_year = Column(Integer, nullable=True)
    
    # Оценка и заметки
    rating = Column(Integer, nullable=True)  # 1-10
    notes = Column(Text, nullable=True)
    quotes = Column(JSON, default=list)  # Список цитат
    
    # Физическое расположение
    location = Column(String(255), nullable=True)
    
    # Внешние данные
    cover_url = Column(String(1000), nullable=True)
    external_id = Column(String(100), nullable=True)  # ID из Google Books/Open Library
    isbn = Column(String(20), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    authors = relationship("Author", secondary=book_authors, back_populates="books")
    genres = relationship("Genre", secondary=book_genres, back_populates="books")
    
    @property
    def progress(self) -> float:
        """Прогресс чтения в процентах"""
        if not self.total_pages or self.total_pages == 0:
            return 0.0
        return round((self.current_page or 0) / self.total_pages * 100, 1)
    
    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}')>"


class ReadingSession(Base):
    """Сессия чтения (для статистики)"""
    __tablename__ = "reading_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    
    date = Column(Date, default=date.today)
    pages_read = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Связь с книгой
    book = relationship("Book", backref="reading_sessions")
    
    def __repr__(self):
        return f"<ReadingSession(id={self.id}, book_id={self.book_id}, pages={self.pages_read})>"
