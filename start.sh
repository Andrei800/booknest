#!/bin/bash
echo "========================================"
echo "  BookNest - Запуск приложения"
echo "========================================"
echo

cd "$(dirname "$0")"

# Проверяем наличие venv
if [ ! -d "venv" ]; then
    echo "[!] Виртуальное окружение не найдено"
    echo "[*] Создаю venv..."
    python3 -m venv venv
    
    echo "[*] Устанавливаю зависимости..."
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

echo
echo "[*] Запускаю BookNest..."
echo "[*] Откройте в браузере: http://localhost:8000"
echo "[*] Документация API: http://localhost:8000/docs"
echo "[*] Для остановки нажмите Ctrl+C"
echo

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
