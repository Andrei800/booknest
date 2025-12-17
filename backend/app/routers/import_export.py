"""
Роутер для импорта и экспорта данных
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import json
import io
from datetime import datetime, date
import chardet

from ..db import get_db
from ..models import Book, Author, Genre
from ..schemas import ImportResult, ExportFormat, BookCreate
from .books import get_or_create_author, get_or_create_genre

router = APIRouter(prefix="/import-export", tags=["import-export"])


def detect_encoding(content: bytes) -> str:
    """Автоматическое определение кодировки файла"""
    result = chardet.detect(content)
    encoding = result.get('encoding', 'utf-8')
    confidence = result.get('confidence', 0)
    
    # Если уверенность низкая, пробуем UTF-8
    if confidence < 0.7:
        try:
            content.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass
    
    return encoding or 'utf-8'

def parse_date(date_str: str) -> Optional[date]:
    """Парсинг даты из различных форматов"""
    if not date_str or date_str.strip() == '':
        return None
    
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%d.%m.%Y',
        '%d/%m/%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def map_reading_status(status: str, state: str) -> str:
    """Маппинг статуса чтения из Book Tracker в наш формат"""
    status_lower = (status or '').lower()
    
    if status_lower == 'read':
        return 'finished'
    elif status_lower == 'reading':
        return 'reading'
    elif status_lower == 'want_to_read':
        return 'planned'
    elif status_lower == 'on_hold':
        return 'on_hold'
    elif status_lower == 'dropped':
        return 'dropped'
    else:
        # Если статус не определён, смотрим на state
        state_lower = (state or '').lower()
        if state_lower in ['bookshelf', 'owned']:
            return 'planned'
        return 'planned'


def map_book_format(types: str) -> str:
    """Маппинг формата книги из Book Tracker"""
    types_lower = (types or '').lower()
    
    if 'audiobook' in types_lower:
        return 'audiobook'
    elif 'ebook' in types_lower or 'e-book' in types_lower:
        return 'ebook'
    elif 'hardcover' in types_lower:
        return 'paper'
    elif 'paperback' in types_lower:
        return 'paper'
    else:
        return 'paper'


@router.post("/import/booktracker", response_model=ImportResult)
async def import_from_booktracker(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Импорт книг из CSV файла приложения Book Tracker.
    
    Поддерживаемые колонки Book Tracker:
    - title, subtitle, authors, categories
    - readingStatus (read/reading/want_to_read)
    - types (PAPERBACK/EBOOK/AUDIOBOOK/HARDCOVER)
    - pages, userRating, languages
    - remoteImageUrl, description
    - startReading, endReading
    - location, publishers, isbn10, isbn13
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате CSV")
    
    result = ImportResult()
    
    try:
        content = await file.read()
        
        # Определяем кодировку автоматически
        encoding = detect_encoding(content)
        
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            # Fallback к UTF-8 с игнорированием ошибок
            text = content.decode('utf-8', errors='replace')
        
        # Book Tracker использует ; как разделитель
        # Определяем разделитель автоматически
        first_line = text.split('\n')[0] if '\n' in text else text
        delimiter = ';' if ';' in first_line else ','
        
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        
        for row_num, row in enumerate(reader, start=2):
            try:
                title = row.get('title', '').strip()
                if not title:
                    result.errors.append(f"Строка {row_num}: пустое название")
                    result.failed += 1
                    continue
                
                # Проверяем дубликаты
                existing = db.query(Book).filter(Book.title == title).first()
                if existing:
                    result.errors.append(f"Строка {row_num}: книга '{title}' уже существует")
                    result.skipped += 1
                    continue
                
                # Парсим авторов (разделены запятой внутри ячейки)
                authors_str = row.get('authors', '')
                authors = [a.strip() for a in authors_str.split(',') if a.strip()]
                
                # Парсим жанры/категории
                categories_str = row.get('categories', '') or row.get('tags', '')
                genres = [g.strip() for g in categories_str.split(',') if g.strip()]
                
                # Маппинг статуса
                reading_status = map_reading_status(
                    row.get('readingStatus', ''),
                    row.get('state', '')
                )
                
                # Маппинг формата
                book_format = map_book_format(row.get('types', ''))
                
                # Язык
                language = row.get('languages', 'ru').strip() or 'ru'
                if ',' in language:
                    language = language.split(',')[0].strip()
                
                # Создаём книгу
                book = Book(
                    title=title,
                    subtitle=row.get('subtitle', '').strip() or None,
                    description=row.get('description', '').strip() or None,
                    language=language[:10],  # Ограничиваем длину
                    format=book_format,
                    status=reading_status,
                    location=row.get('location', '').strip() or None,
                    cover_url=row.get('remoteImageUrl', '').strip() or row.get('thumbnailRemoteImageUrl', '').strip() or None,
                )
                
                # ISBN
                isbn = row.get('isbn13', '').strip() or row.get('isbn10', '').strip()
                if isbn:
                    book.isbn = isbn
                
                # Страницы
                pages_str = row.get('pages', '').strip()
                if pages_str:
                    try:
                        book.total_pages = int(pages_str)
                    except ValueError:
                        pass
                
                # Рейтинг (Book Tracker использует 1-5 или 1-10?)
                rating_str = row.get('userRating', '').strip()
                if rating_str:
                    try:
                        rating = float(rating_str)
                        # Если рейтинг от 1 до 5, умножаем на 2
                        if rating <= 5:
                            rating = int(rating * 2)
                        else:
                            rating = int(rating)
                        if 1 <= rating <= 10:
                            book.rating = rating
                    except ValueError:
                        pass
                
                # Год издания
                release_year = row.get('releaseYear', '').strip() or row.get('originalReleaseYear', '').strip()
                if release_year:
                    try:
                        book.published_year = int(release_year)
                    except ValueError:
                        pass
                
                # Даты чтения
                start_reading = row.get('startReading', '').strip()
                end_reading = row.get('endReading', '').strip()
                
                start_date = parse_date(start_reading)
                end_date = parse_date(end_reading)
                
                if start_date:
                    book.started_at = datetime.combine(start_date, datetime.min.time())
                if end_date:
                    book.finished_at = datetime.combine(end_date, datetime.min.time())
                
                # Если книга прочитана, устанавливаем прогресс 100%
                if reading_status == 'finished' and book.total_pages:
                    book.current_page = book.total_pages
                
                # Сначала добавляем книгу в сессию
                db.add(book)
                db.flush()  # Получаем ID книги
                
                # Добавляем авторов (убираем дубликаты)
                seen_authors = set()
                for author_name in authors:
                    author_lower = author_name.lower().strip()
                    if author_lower and author_lower not in seen_authors:
                        seen_authors.add(author_lower)
                        author = get_or_create_author(db, author_name)
                        if author not in book.authors:
                            book.authors.append(author)
                
                # Добавляем жанры (убираем дубликаты)
                seen_genres = set()
                for genre_name in genres:
                    genre_lower = genre_name.lower().strip()
                    if genre_lower and genre_lower not in seen_genres:
                        seen_genres.add(genre_lower)
                        genre = get_or_create_genre(db, genre_name)
                        if genre not in book.genres:
                            book.genres.append(genre)
                
                # Коммитим каждую книгу отдельно
                db.commit()
                result.success += 1
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                result.errors.append(f"Строка {row_num}: {str(e)}")
                result.failed += 1
                db.rollback()
        
        # Финальный коммит (если что-то осталось)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")
    
    return result


@router.post("/import/csv", response_model=ImportResult)
async def import_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Импорт книг из CSV файла.
    
    Ожидаемые колонки:
    - title (обязательно)
    - authors (через запятую)
    - genres (через запятую)
    - status (planned/reading/finished/on_hold/dropped)
    - format (paper/ebook/audiobook)
    - language
    - total_pages
    - current_page
    - rating (1-10)
    - notes
    - location
    - published_year
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате CSV")
    
    result = ImportResult()
    
    try:
        content = await file.read()
        # Пробуем разные кодировки
        for encoding in ['utf-8', 'cp1251', 'latin-1']:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="Не удалось определить кодировку файла")
        
        reader = csv.DictReader(io.StringIO(text))
        
        for row_num, row in enumerate(reader, start=2):
            try:
                title = row.get('title', '').strip()
                if not title:
                    result.errors.append(f"Строка {row_num}: пустое название")
                    result.failed += 1
                    continue
                
                # Парсим авторов
                authors_str = row.get('authors', '') or row.get('author', '')
                authors = [a.strip() for a in authors_str.split(',') if a.strip()]
                
                # Парсим жанры
                genres_str = row.get('genres', '') or row.get('genre', '')
                genres = [g.strip() for g in genres_str.split(',') if g.strip()]
                
                # Создаём книгу
                book = Book(
                    title=title,
                    subtitle=row.get('subtitle', '').strip() or None,
                    description=row.get('description', '').strip() or None,
                    language=row.get('language', 'ru').strip() or 'ru',
                    format=row.get('format', 'paper').strip() or 'paper',
                    status=row.get('status', 'planned').strip() or 'planned',
                    location=row.get('location', '').strip() or None,
                    notes=row.get('notes', '').strip() or None,
                )
                
                # Числовые поля
                if row.get('total_pages'):
                    try:
                        book.total_pages = int(row['total_pages'])
                    except ValueError:
                        pass
                
                if row.get('current_page'):
                    try:
                        book.current_page = int(row['current_page'])
                    except ValueError:
                        pass
                
                if row.get('rating'):
                    try:
                        rating = int(row['rating'])
                        if 1 <= rating <= 10:
                            book.rating = rating
                    except ValueError:
                        pass
                
                if row.get('published_year'):
                    try:
                        book.published_year = int(row['published_year'])
                    except ValueError:
                        pass
                
                # Добавляем авторов и жанры
                for author_name in authors:
                    author = get_or_create_author(db, author_name)
                    book.authors.append(author)
                
                for genre_name in genres:
                    genre = get_or_create_genre(db, genre_name)
                    book.genres.append(genre)
                
                db.add(book)
                result.success += 1
                
            except Exception as e:
                result.errors.append(f"Строка {row_num}: {str(e)}")
                result.failed += 1
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")
    
    return result


@router.post("/import/json", response_model=ImportResult)
async def import_from_json(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Импорт книг из JSON файла"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате JSON")
    
    result = ImportResult()
    
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        books_data = data if isinstance(data, list) else data.get('books', [])
        
        for i, book_data in enumerate(books_data):
            try:
                title = book_data.get('title', '').strip()
                if not title:
                    result.errors.append(f"Книга {i+1}: пустое название")
                    result.failed += 1
                    continue
                
                book = Book(
                    title=title,
                    subtitle=book_data.get('subtitle'),
                    description=book_data.get('description'),
                    language=book_data.get('language', 'ru'),
                    format=book_data.get('format', 'paper'),
                    status=book_data.get('status', 'planned'),
                    total_pages=book_data.get('total_pages'),
                    current_page=book_data.get('current_page', 0),
                    rating=book_data.get('rating'),
                    notes=book_data.get('notes'),
                    quotes=book_data.get('quotes', []),
                    location=book_data.get('location'),
                    cover_url=book_data.get('cover_url'),
                    published_year=book_data.get('published_year'),
                    isbn=book_data.get('isbn'),
                )
                
                # Авторы
                authors = book_data.get('authors', [])
                if isinstance(authors, str):
                    authors = [authors]
                for author_name in authors:
                    if author_name:
                        author = get_or_create_author(db, author_name.strip())
                        book.authors.append(author)
                
                # Жанры
                genres = book_data.get('genres', [])
                if isinstance(genres, str):
                    genres = [genres]
                for genre_name in genres:
                    if genre_name:
                        genre = get_or_create_genre(db, genre_name.strip())
                        book.genres.append(genre)
                
                db.add(book)
                result.success += 1
                
            except Exception as e:
                result.errors.append(f"Книга {i+1}: {str(e)}")
                result.failed += 1
        
        db.commit()
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга JSON: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")
    
    return result


@router.get("/export/csv")
def export_to_csv(db: Session = Depends(get_db)):
    """Экспорт всех книг в CSV"""
    books = db.query(Book).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    headers = [
        'id', 'title', 'subtitle', 'authors', 'genres', 'language',
        'format', 'status', 'total_pages', 'current_page', 'progress',
        'started_at', 'finished_at', 'published_year', 'rating',
        'notes', 'location', 'cover_url', 'isbn', 'created_at'
    ]
    writer.writerow(headers)
    
    # Данные
    for book in books:
        authors = ', '.join([a.name for a in book.authors])
        genres = ', '.join([g.name for g in book.genres])
        
        writer.writerow([
            book.id,
            book.title,
            book.subtitle or '',
            authors,
            genres,
            book.language,
            book.format,
            book.status,
            book.total_pages or '',
            book.current_page or 0,
            book.progress,
            book.started_at.isoformat() if book.started_at else '',
            book.finished_at.isoformat() if book.finished_at else '',
            book.published_year or '',
            book.rating or '',
            book.notes or '',
            book.location or '',
            book.cover_url or '',
            book.isbn or '',
            book.created_at.isoformat() if book.created_at else '',
        ])
    
    output.seek(0)
    
    filename = f"booknest_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/json")
def export_to_json(
    pretty: bool = Query(True, description="Форматированный JSON"),
    db: Session = Depends(get_db)
):
    """Экспорт всех книг в JSON"""
    books = db.query(Book).all()
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "total_books": len(books),
        "books": []
    }
    
    for book in books:
        book_data = {
            "id": book.id,
            "title": book.title,
            "subtitle": book.subtitle,
            "authors": [a.name for a in book.authors],
            "genres": [g.name for g in book.genres],
            "description": book.description,
            "language": book.language,
            "format": book.format,
            "status": book.status,
            "total_pages": book.total_pages,
            "current_page": book.current_page,
            "progress": book.progress,
            "started_at": book.started_at.isoformat() if book.started_at else None,
            "finished_at": book.finished_at.isoformat() if book.finished_at else None,
            "published_year": book.published_year,
            "rating": book.rating,
            "notes": book.notes,
            "quotes": book.quotes,
            "location": book.location,
            "cover_url": book.cover_url,
            "isbn": book.isbn,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "updated_at": book.updated_at.isoformat() if book.updated_at else None,
        }
        data["books"].append(book_data)
    
    indent = 2 if pretty else None
    json_str = json.dumps(data, ensure_ascii=False, indent=indent)
    
    filename = f"booknest_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        iter([json_str]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/template/csv")
def get_csv_template():
    """Скачать шаблон CSV для импорта"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        'title', 'authors', 'genres', 'language', 'format', 'status',
        'total_pages', 'current_page', 'rating', 'notes', 'location', 'published_year'
    ]
    writer.writerow(headers)
    
    # Пример строки
    writer.writerow([
        'Мастер и Маргарита',
        'Михаил Булгаков',
        'Классика, Фантастика',
        'ru',
        'paper',
        'finished',
        '480',
        '480',
        '10',
        'Отличная книга!',
        'Полка 2',
        '1966'
    ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=booknest_import_template.csv"}
    )


@router.get("/export/pdf")
def export_pdf(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db)
):
    """Экспорт библиотеки в PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    
    # Регистрируем шрифт с поддержкой кириллицы
    # Используем встроенный шрифт DejaVu если доступен
    try:
        font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'DejaVuSans.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            font_name = 'DejaVu'
        else:
            # Пробуем системный Arial
            font_name = 'Helvetica'
    except:
        font_name = 'Helvetica'
    
    # Запрос книг
    query = db.query(Book)
    if status:
        query = query.filter(Book.status == status)
    books = query.order_by(Book.title).all()
    
    # Создаём PDF в памяти
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Заголовок
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # center
    )
    elements.append(Paragraph("BookNest - Моя библиотека", title_style))
    
    # Статистика
    total = len(books)
    finished = sum(1 for b in books if b.status == 'finished')
    reading = sum(1 for b in books if b.status == 'reading')
    planned = sum(1 for b in books if b.status == 'planned')
    
    stats_text = f"Всего книг: {total} | Прочитано: {finished} | Читаю: {reading} | Хочу прочитать: {planned}"
    stats_style = ParagraphStyle(
        'Stats',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=20,
        alignment=1
    )
    elements.append(Paragraph(stats_text, stats_style))
    elements.append(Spacer(1, 20))
    
    status_map = {
        'planned': 'Хочу прочитать',
        'reading': 'Читаю',
        'finished': 'Прочитано',
        'on_hold': 'Отложено',
        'dropped': 'Брошено',
        'wishlist': 'Хотелки'
    }
    
    # Таблица книг
    data = [['№', 'Название', 'Автор', 'Статус', 'Оценка', 'Стр.']]
    
    for i, book in enumerate(books, 1):
        authors = ', '.join([a.name for a in book.authors]) or '-'
        status_text = status_map.get(book.status, book.status)
        rating = f"{book.rating}/10" if book.rating else '-'
        pages = str(book.total_pages) if book.total_pages else '-'
        
        # Ограничиваем длину названия и автора
        title_text = book.title[:40] + '...' if len(book.title) > 40 else book.title
        authors_text = authors[:30] + '...' if len(authors) > 30 else authors
        
        data.append([str(i), title_text, authors_text, status_text, rating, pages])
    
    # Создаём таблицу
    col_widths = [0.8*cm, 6*cm, 4*cm, 3*cm, 1.5*cm, 1.5*cm]
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # Футер с датой
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=1
    )
    elements.append(Paragraph(f"Экспортировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"booknest_library_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
