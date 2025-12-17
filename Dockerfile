# Используем Python 3.11
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY . .

# Создаём директорию для данных
RUN mkdir -p /app/data

# Порт
EXPOSE 8000

# Запуск
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
