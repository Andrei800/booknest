@echo off
echo ========================================
echo   BookNest - Запуск приложения
echo ========================================
echo.

cd /d "%~dp0"

REM Проверяем наличие venv
if not exist "venv\Scripts\activate.bat" (
    echo [!] Виртуальное окружение не найдено
    echo [*] Создаю venv...
    python -m venv venv
    
    echo [*] Устанавливаю зависимости...
    call venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [*] Запускаю BookNest...
echo [*] Откройте в браузере: http://localhost:8000
echo [*] Документация API: http://localhost:8000/docs
echo [*] Для остановки нажмите Ctrl+C
echo.

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
