"""
AI-сервис для умных функций приложения
"""
import httpx
from typing import Optional
import json

from ..config import get_settings
from ..models import Book

settings = get_settings()


async def generate_book_summary(title: str, author: str | None, notes: str | None) -> str | None:
    """
    Генерация краткого описания книги с помощью LLM.
    Использует OpenAI API если доступен ключ.
    """
    if not settings.OPENAI_API_KEY:
        return None
    
    prompt = f'Напиши краткое описание (2-3 предложения) книги "{title}"'
    if author:
        prompt += f" автора {author}"
    prompt += ". Описание должно быть информативным и интересным."
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'system', 'content': 'Ты — помощник библиотекаря. Пиши кратко и информативно на русском языке.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 200,
                    'temperature': 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
    
    return None


async def generate_recommendations(
    finished_books: list[dict],
    favorite_genres: list[str],
    favorite_authors: list[str],
    count: int = 5
) -> list[dict]:
    """
    Генерация рекомендаций книг на основе прочитанных.
    """
    if not settings.OPENAI_API_KEY:
        return []
    
    # Формируем контекст
    books_info = []
    for book in finished_books[:10]:  # Берём последние 10 книг
        info = f"- {book['title']}"
        if book.get('authors'):
            info += f" ({', '.join(book['authors'])})"
        if book.get('rating'):
            info += f" — оценка {book['rating']}/10"
        books_info.append(info)
    
    prompt = f"""На основе прочитанных книг пользователя порекомендуй {count} новых книг.

Прочитанные книги:
{chr(10).join(books_info)}

Любимые жанры: {', '.join(favorite_genres) if favorite_genres else 'не указаны'}
Любимые авторы: {', '.join(favorite_authors) if favorite_authors else 'не указаны'}

Ответь в формате JSON массива:
[
  {{"title": "Название", "author": "Автор", "reason": "Почему рекомендуем"}}
]

Только JSON, без дополнительного текста."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'system', 'content': 'Ты — эксперт по книгам. Отвечай только валидным JSON.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 500,
                    'temperature': 0.8
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                
                # Пробуем распарсить JSON
                try:
                    # Убираем возможные markdown-блоки
                    if content.startswith('```'):
                        content = content.split('```')[1]
                        if content.startswith('json'):
                            content = content[4:]
                    
                    recommendations = json.loads(content)
                    return recommendations
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"OpenAI API error: {e}")
    
    return []


async def summarize_notes(notes: str, quotes: list[str]) -> str | None:
    """
    Создание краткого резюме заметок и цитат из книги.
    """
    if not settings.OPENAI_API_KEY:
        return None
    
    if not notes and not quotes:
        return None
    
    content_parts = []
    if notes:
        content_parts.append(f"Заметки:\n{notes}")
    if quotes:
        content_parts.append(f"Цитаты:\n" + "\n".join(f"• {q}" for q in quotes))
    
    prompt = f"""Создай краткое резюме (3-5 предложений) на основе заметок и цитат пользователя о книге:

{chr(10).join(content_parts)}

Резюме должно отражать основные мысли и впечатления."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'system', 'content': 'Ты — помощник для ведения читательского дневника. Пиши на русском языке.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 300,
                    'temperature': 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
    
    return None


def get_simple_recommendations(books: list[Book], limit: int = 5) -> list[dict]:
    """
    Простые рекомендации на основе правил (без LLM).
    Анализирует прочитанные книги и предлагает искать похожие.
    """
    # Собираем статистику
    genre_counts = {}
    author_counts = {}
    
    for book in books:
        if book.status != 'finished':
            continue
        
        for genre in book.genres:
            genre_counts[genre.name] = genre_counts.get(genre.name, 0) + 1
        
        for author in book.authors:
            author_counts[author.name] = author_counts.get(author.name, 0) + 1
    
    # Топ жанры
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Топ авторы
    top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    recommendations = []
    
    # Рекомендации по жанрам
    for genre, count in top_genres:
        recommendations.append({
            'type': 'genre',
            'value': genre,
            'reason': f'Вам нравится жанр "{genre}" ({count} прочитанных книг)',
            'search_query': f'жанр:{genre}'
        })
    
    # Рекомендации по авторам
    for author, count in top_authors:
        recommendations.append({
            'type': 'author',
            'value': author,
            'reason': f'Вы читали {count} книг автора {author}',
            'search_query': f'автор:{author}'
        })
    
    return recommendations[:limit]
