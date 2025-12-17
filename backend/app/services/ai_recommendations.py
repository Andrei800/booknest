"""
AI Book Recommendations using Google Gemini
"""
import httpx
import json
import re
from typing import Optional

GEMINI_API_KEY = "AIzaSyAhl_SD8TPUWNLb2-6PHnNoDsa4I-yOCtI"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


async def get_book_recommendations(
    title: str,
    authors: list[str],
    genres: list[str],
    notes: Optional[str] = None,
    language: str = "ru"
) -> dict:
    """
    Получить AI-рекомендации похожих книг на основе данных о книге.
    """
    
    authors_str = ", ".join(authors) if authors else "неизвестен"
    genres_str = ", ".join(genres) if genres else "не указаны"
    
    prompt = f"""Ты - эксперт по книгам и литературе. Пользователю понравилась книга:

Название: {title}
Автор(ы): {authors_str}
Жанры: {genres_str}
{f"Заметки пользователя: {notes}" if notes else ""}

Порекомендуй 5 похожих книг, которые могут понравиться читателю. Учитывай:
- Схожий стиль написания
- Похожие темы и сюжеты
- Тот же или близкий жанр
- Похожую атмосферу

Ответь ТОЛЬКО в формате JSON (без markdown, без ```):
{{
    "recommendations": [
        {{
            "title": "Название книги",
            "author": "Автор",
            "reason": "Краткое объяснение почему эта книга похожа (1-2 предложения)",
            "genres": ["жанр1", "жанр2"]
        }}
    ],
    "summary": "Общий комментарий о том, что объединяет эти рекомендации (1 предложение)"
}}

Отвечай на русском языке."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 2048,
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"Gemini API error: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}
            
            data = response.json()
            
            # Извлекаем текст ответа
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Очищаем от markdown если есть
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Парсим JSON
            try:
                result = json.loads(text)
                return result
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}, text: {text[:500]}")
                # Пробуем найти JSON в тексте
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        return result
                    except:
                        pass
                return {"error": "Failed to parse AI response", "raw": text[:500]}
                
    except httpx.TimeoutException:
        return {"error": "AI request timeout"}
    except Exception as e:
        print(f"AI recommendation error: {e}")
        return {"error": str(e)}


async def get_reading_insights(books: list[dict]) -> dict:
    """
    Получить AI-анализ читательских предпочтений на основе библиотеки.
    """
    
    if not books:
        return {"error": "No books to analyze"}
    
    # Собираем информацию о книгах
    books_info = []
    for book in books[:30]:  # Ограничиваем до 30 книг
        info = f"- {book.get('title', 'Unknown')}"
        if book.get('authors'):
            authors = [a.get('name', '') for a in book['authors']]
            info += f" ({', '.join(authors)})"
        if book.get('rating'):
            info += f" - оценка {book['rating']}/10"
        if book.get('status') == 'completed':
            info += " [прочитано]"
        books_info.append(info)
    
    prompt = f"""Проанализируй библиотеку пользователя и дай insights о его читательских предпочтениях:

Книги:
{chr(10).join(books_info)}

Ответь ТОЛЬКО в формате JSON (без markdown):
{{
    "favorite_genres": ["жанр1", "жанр2", "жанр3"],
    "reading_style": "Краткое описание стиля чтения (1-2 предложения)",
    "personality_traits": ["черта1", "черта2", "черта3"],
    "recommendation_direction": "В каком направлении стоит расширить круг чтения (1-2 предложения)",
    "fun_fact": "Интересный факт о библиотеке пользователя"
}}

Отвечай на русском."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 1024,
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return {"error": f"API error: {response.status_code}"}
            
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Очищаем от markdown
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            try:
                return json.loads(text)
            except:
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    return json.loads(json_match.group())
                return {"error": "Failed to parse response"}
                
    except Exception as e:
        return {"error": str(e)}
