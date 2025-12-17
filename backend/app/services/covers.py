"""
Сервис для поиска обложек и метаданных книг
Использует Google Books API и Open Library API
"""
import httpx
from typing import Optional
import asyncio

from ..schemas import CoverSearchResult
from ..config import get_settings

settings = get_settings()


async def search_google_books(title: str, author: str | None = None) -> CoverSearchResult | None:
    """
    Поиск книги в Google Books API
    https://developers.google.com/books/docs/v1/using
    """
    try:
        # Формируем поисковый запрос
        query = f'intitle:{title}'
        if author:
            query += f'+inauthor:{author}'
        
        params = {
            'q': query,
            'maxResults': 5,
            'printType': 'books',
            'langRestrict': 'ru',  # Предпочитаем русские книги
        }
        
        # Добавляем API ключ если есть
        if settings.GOOGLE_BOOKS_API_KEY:
            params['key'] = settings.GOOGLE_BOOKS_API_KEY
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                'https://www.googleapis.com/books/v1/volumes',
                params=params
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data.get('items'):
                # Попробуем без языкового ограничения
                del params['langRestrict']
                response = await client.get(
                    'https://www.googleapis.com/books/v1/volumes',
                    params=params
                )
                if response.status_code != 200:
                    return None
                data = response.json()
            
            if not data.get('items'):
                return None
            
            # Берём первый результат
            item = data['items'][0]
            volume_info = item.get('volumeInfo', {})
            
            # Получаем URL обложки (предпочитаем большую)
            image_links = volume_info.get('imageLinks', {})
            cover_url = (
                image_links.get('large') or
                image_links.get('medium') or
                image_links.get('small') or
                image_links.get('thumbnail') or
                image_links.get('smallThumbnail')
            )
            
            # Заменяем http на https и убираем zoom=1
            if cover_url:
                cover_url = cover_url.replace('http://', 'https://')
                cover_url = cover_url.replace('&edge=curl', '')
            
            # Год публикации
            published_year = None
            published_date = volume_info.get('publishedDate', '')
            if published_date:
                try:
                    published_year = int(published_date[:4])
                except ValueError:
                    pass
            
            return CoverSearchResult(
                cover_url=cover_url,
                description=volume_info.get('description'),
                published_year=published_year,
                external_id=item.get('id'),
                source='google_books'
            )
            
    except Exception as e:
        print(f"Google Books API error: {e}")
        return None


async def search_open_library(title: str, author: str | None = None) -> CoverSearchResult | None:
    """
    Поиск книги в Open Library API
    https://openlibrary.org/dev/docs/api/search
    """
    try:
        params = {
            'title': title,
            'limit': 5
        }
        if author:
            params['author'] = author
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                'https://openlibrary.org/search.json',
                params=params
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data.get('docs'):
                return None
            
            # Берём первый результат
            doc = data['docs'][0]
            
            # Получаем обложку по cover_i
            cover_url = None
            cover_id = doc.get('cover_i')
            if cover_id:
                cover_url = f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg'
            
            # Альтернативно по ISBN
            if not cover_url:
                isbn = doc.get('isbn', [None])[0]
                if isbn:
                    cover_url = f'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
            
            # Год публикации
            published_year = doc.get('first_publish_year')
            
            # Описание (нужен дополнительный запрос)
            description = None
            work_key = doc.get('key')
            if work_key:
                try:
                    work_response = await client.get(
                        f'https://openlibrary.org{work_key}.json'
                    )
                    if work_response.status_code == 200:
                        work_data = work_response.json()
                        desc = work_data.get('description')
                        if isinstance(desc, dict):
                            description = desc.get('value')
                        elif isinstance(desc, str):
                            description = desc
                except:
                    pass
            
            return CoverSearchResult(
                cover_url=cover_url,
                description=description,
                published_year=published_year,
                external_id=doc.get('key'),
                source='open_library'
            )
            
    except Exception as e:
        print(f"Open Library API error: {e}")
        return None


async def fetch_book_metadata(title: str, author: str | None = None) -> CoverSearchResult | None:
    """
    Поиск метаданных книги из разных источников.
    Сначала пробует Google Books, затем Open Library.
    """
    # Пробуем Google Books
    result = await search_google_books(title, author)
    if result and result.cover_url:
        return result
    
    # Пробуем Open Library
    result = await search_open_library(title, author)
    if result and result.cover_url:
        return result
    
    # Возвращаем что есть (может быть описание без обложки)
    return result


async def search_by_isbn(isbn: str) -> dict | None:
    """
    Поиск книги по ISBN через Google Books и Open Library.
    Возвращает полные метаданные книги.
    """
    # Очищаем ISBN от дефисов и пробелов
    isbn = isbn.replace('-', '').replace(' ', '').strip()
    
    result = {
        'isbn': isbn,
        'title': None,
        'authors': [],
        'cover_url': None,
        'description': None,
        'published_year': None,
        'total_pages': None,
        'genres': [],
        'language': None,
    }
    
    # Пробуем Google Books по ISBN
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                'https://www.googleapis.com/books/v1/volumes',
                params={'q': f'isbn:{isbn}', 'maxResults': 1}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    item = data['items'][0]
                    volume_info = item.get('volumeInfo', {})
                    
                    result['title'] = volume_info.get('title')
                    result['authors'] = volume_info.get('authors', [])
                    result['description'] = volume_info.get('description')
                    result['total_pages'] = volume_info.get('pageCount')
                    result['language'] = volume_info.get('language')
                    result['genres'] = volume_info.get('categories', [])
                    
                    # Год публикации
                    published_date = volume_info.get('publishedDate', '')
                    if published_date:
                        try:
                            result['published_year'] = int(published_date[:4])
                        except ValueError:
                            pass
                    
                    # Обложка
                    image_links = volume_info.get('imageLinks', {})
                    cover_url = (
                        image_links.get('large') or
                        image_links.get('medium') or
                        image_links.get('thumbnail')
                    )
                    if cover_url:
                        result['cover_url'] = cover_url.replace('http://', 'https://')
                    
                    if result['title']:
                        return result
    except Exception as e:
        print(f"Google Books ISBN search error: {e}")
    
    # Пробуем Open Library по ISBN
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f'https://openlibrary.org/isbn/{isbn}.json'
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result['title'] = data.get('title')
                result['total_pages'] = data.get('number_of_pages')
                
                # Обложка
                covers = data.get('covers', [])
                if covers:
                    result['cover_url'] = f'https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg'
                else:
                    result['cover_url'] = f'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
                
                # Для получения авторов нужен дополнительный запрос
                author_keys = data.get('authors', [])
                for author_ref in author_keys:
                    author_key = author_ref.get('key')
                    if author_key:
                        try:
                            author_response = await client.get(
                                f'https://openlibrary.org{author_key}.json'
                            )
                            if author_response.status_code == 200:
                                author_data = author_response.json()
                                result['authors'].append(author_data.get('name', ''))
                        except:
                            pass
                
                # Год публикации
                result['published_year'] = data.get('publish_date')
                if result['published_year']:
                    try:
                        result['published_year'] = int(str(result['published_year'])[:4])
                    except ValueError:
                        result['published_year'] = None
                
                if result['title']:
                    return result
    except Exception as e:
        print(f"Open Library ISBN search error: {e}")
    
    return None if not result['title'] else result


async def search_multiple_covers(title: str, author: str | None = None, limit: int = 8) -> list[dict]:
    """
    Поиск нескольких вариантов обложек для книги.
    Возвращает список с разными вариантами из Google Books и Open Library.
    """
    covers = []
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Google Books - несколько результатов
            query = f'intitle:{title}'
            if author:
                query += f'+inauthor:{author}'
            
            params = {
                'q': query,
                'maxResults': 10,
                'printType': 'books',
            }
            if settings.GOOGLE_BOOKS_API_KEY:
                params['key'] = settings.GOOGLE_BOOKS_API_KEY
            
            response = await client.get(
                'https://www.googleapis.com/books/v1/volumes',
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', []):
                    volume = item.get('volumeInfo', {})
                    image_links = volume.get('imageLinks', {})
                    
                    # Получаем лучшее качество
                    cover_url = (
                        image_links.get('extraLarge') or
                        image_links.get('large') or
                        image_links.get('medium') or
                        image_links.get('small') or
                        image_links.get('thumbnail')
                    )
                    
                    if cover_url:
                        cover_url = cover_url.replace('http://', 'https://').replace('&edge=curl', '')
                        # Увеличиваем размер если есть zoom параметр
                        if 'zoom=' in cover_url:
                            cover_url = cover_url.replace('zoom=1', 'zoom=3')
                        
                        covers.append({
                            'url': cover_url,
                            'source': 'Google Books',
                            'title': volume.get('title', ''),
                            'authors': ', '.join(volume.get('authors', [])),
                        })
            
            # Open Library - несколько результатов
            ol_params = {'title': title, 'limit': 10}
            if author:
                ol_params['author'] = author
            
            ol_response = await client.get(
                'https://openlibrary.org/search.json',
                params=ol_params
            )
            
            if ol_response.status_code == 200:
                ol_data = ol_response.json()
                for doc in ol_data.get('docs', []):
                    cover_id = doc.get('cover_i')
                    if cover_id:
                        covers.append({
                            'url': f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg',
                            'source': 'Open Library',
                            'title': doc.get('title', ''),
                            'authors': ', '.join(doc.get('author_name', [])),
                        })
                    
                    # Также по ISBN
                    isbns = doc.get('isbn', [])
                    if isbns and not cover_id:
                        covers.append({
                            'url': f'https://covers.openlibrary.org/b/isbn/{isbns[0]}-L.jpg',
                            'source': 'Open Library (ISBN)',
                            'title': doc.get('title', ''),
                            'authors': ', '.join(doc.get('author_name', [])),
                        })
                        
    except Exception as e:
        print(f"Multiple covers search error: {e}")
    
    # Убираем дубликаты по URL
    seen_urls = set()
    unique_covers = []
    for cover in covers:
        if cover['url'] not in seen_urls:
            seen_urls.add(cover['url'])
            unique_covers.append(cover)
    
    return unique_covers[:limit]


async def search_books_by_query(query: str, limit: int = 10) -> list[dict]:
    """
    Поиск книг по запросу для автодополнения
    """
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Google Books
            params = {
                'q': query,
                'maxResults': limit,
                'printType': 'books'
            }
            if settings.GOOGLE_BOOKS_API_KEY:
                params['key'] = settings.GOOGLE_BOOKS_API_KEY
            
            response = await client.get(
                'https://www.googleapis.com/books/v1/volumes',
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', []):
                    volume = item.get('volumeInfo', {})
                    image_links = volume.get('imageLinks', {})
                    
                    results.append({
                        'title': volume.get('title', ''),
                        'subtitle': volume.get('subtitle'),
                        'authors': volume.get('authors', []),
                        'published_year': volume.get('publishedDate', '')[:4] if volume.get('publishedDate') else None,
                        'description': volume.get('description'),
                        'cover_url': image_links.get('thumbnail', '').replace('http://', 'https://'),
                        'external_id': item.get('id'),
                        'source': 'google_books'
                    })
    except Exception as e:
        print(f"Search error: {e}")
    
    return results[:limit]
