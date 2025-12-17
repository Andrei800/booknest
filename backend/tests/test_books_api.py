"""
Тесты для API книг
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.models import Book, Author, Genre


# Тестовая база данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Переопределение зависимости БД для тестов"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Создание таблиц перед каждым тестом"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Тестовый клиент"""
    return TestClient(app)


@pytest.fixture
def sample_book_data():
    """Пример данных книги"""
    return {
        "title": "Мастер и Маргарита",
        "authors": ["Михаил Булгаков"],
        "genres": ["Классика", "Фантастика"],
        "language": "ru",
        "format": "paper",
        "status": "planned",
        "total_pages": 480,
        "auto_fetch_cover": False
    }


class TestBooksAPI:
    """Тесты для эндпоинтов книг"""
    
    def test_create_book(self, client, sample_book_data):
        """Тест создания книги"""
        response = client.post("/api/books", json=sample_book_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["title"] == sample_book_data["title"]
        assert len(data["authors"]) == 1
        assert data["authors"][0]["name"] == "Михаил Булгаков"
        assert len(data["genres"]) == 2
        assert data["status"] == "planned"
    
    def test_get_books_empty(self, client):
        """Тест получения пустого списка книг"""
        response = client.get("/api/books")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    def test_get_books_list(self, client, sample_book_data):
        """Тест получения списка книг"""
        # Создаём книгу
        client.post("/api/books", json=sample_book_data)
        
        response = client.get("/api/books")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
    
    def test_get_book_by_id(self, client, sample_book_data):
        """Тест получения книги по ID"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        response = client.get(f"/api/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["title"] == sample_book_data["title"]
    
    def test_get_book_not_found(self, client):
        """Тест получения несуществующей книги"""
        response = client.get("/api/books/999")
        assert response.status_code == 404
    
    def test_update_book(self, client, sample_book_data):
        """Тест обновления книги"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        update_data = {
            "status": "reading",
            "current_page": 100,
            "rating": 9
        }
        
        response = client.patch(f"/api/books/{book_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "reading"
        assert data["current_page"] == 100
        assert data["rating"] == 9
    
    def test_delete_book(self, client, sample_book_data):
        """Тест удаления книги"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        response = client.delete(f"/api/books/{book_id}")
        assert response.status_code == 204
        
        # Проверяем, что книга удалена
        get_response = client.get(f"/api/books/{book_id}")
        assert get_response.status_code == 404
    
    def test_search_books(self, client, sample_book_data):
        """Тест поиска книг"""
        client.post("/api/books", json=sample_book_data)
        
        # Поиск по названию
        response = client.get("/api/books", params={"search": "Мастер"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        
        # Поиск по автору
        response = client.get("/api/books", params={"search": "Булгаков"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        
        # Поиск без результатов
        response = client.get("/api/books", params={"search": "несуществующая"})
        assert response.status_code == 200
        assert response.json()["total"] == 0
    
    def test_filter_by_status(self, client, sample_book_data):
        """Тест фильтрации по статусу"""
        client.post("/api/books", json=sample_book_data)
        
        # Фильтр по статусу planned
        response = client.get("/api/books", params={"status": "planned"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        
        # Фильтр по другому статусу
        response = client.get("/api/books", params={"status": "finished"})
        assert response.status_code == 200
        assert response.json()["total"] == 0
    
    def test_start_reading(self, client, sample_book_data):
        """Тест начала чтения"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        response = client.post(f"/api/books/{book_id}/start-reading")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "reading"
        assert data["started_at"] is not None
    
    def test_finish_reading(self, client, sample_book_data):
        """Тест завершения чтения"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        response = client.post(f"/api/books/{book_id}/finish-reading", params={"rating": 10})
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "finished"
        assert data["finished_at"] is not None
        assert data["rating"] == 10
    
    def test_update_progress(self, client, sample_book_data):
        """Тест обновления прогресса"""
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        response = client.post(f"/api/books/{book_id}/update-progress", params={"current_page": 200})
        assert response.status_code == 200
        
        data = response.json()
        assert data["current_page"] == 200
        assert data["status"] == "reading"  # Автоматически изменился


class TestAuthorsAPI:
    """Тесты для эндпоинтов авторов"""
    
    def test_get_authors_empty(self, client):
        """Тест получения пустого списка авторов"""
        response = client.get("/api/authors")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_author(self, client):
        """Тест создания автора"""
        response = client.post("/api/authors", json={"name": "Лев Толстой"})
        assert response.status_code == 201
        assert response.json()["name"] == "Лев Толстой"
    
    def test_authors_from_book(self, client, sample_book_data):
        """Тест создания авторов через книгу"""
        client.post("/api/books", json=sample_book_data)
        
        response = client.get("/api/authors")
        assert response.status_code == 200
        
        authors = response.json()
        assert len(authors) == 1
        assert authors[0]["name"] == "Михаил Булгаков"


class TestStatsAPI:
    """Тесты для эндпоинтов статистики"""
    
    def test_overview_stats_empty(self, client):
        """Тест статистики без книг"""
        response = client.get("/api/stats/overview")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_books"] == 0
        assert data["books_finished"] == 0
    
    def test_overview_stats_with_books(self, client, sample_book_data):
        """Тест статистики с книгами"""
        # Создаём книгу
        create_response = client.post("/api/books", json=sample_book_data)
        book_id = create_response.json()["id"]
        
        # Завершаем чтение
        client.post(f"/api/books/{book_id}/finish-reading", params={"rating": 8})
        
        response = client.get("/api/stats/overview")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_books"] == 1
        assert data["books_finished"] == 1
