@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo   Парсер вакансий и генератор PDF
echo   Региональный кадровый центр Краснодарского края
echo ============================================================
echo.

REM --- Проверка, что venv есть ---
if not exist ".venv\Scripts\activate.bat" (
    echo [ОШИБКА] Виртуальное окружение .venv не найдено.
    echo.
    echo Создайте его командами:
    echo     python -m venv .venv
    echo     .venv\Scripts\activate
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM --- Активируем venv ---
call .venv\Scripts\activate.bat

REM --- Шаг 1: парсер ---
echo ------------------------------------------------------------
echo   Шаг 1 из 2. Сбор вакансий с сайта
echo ------------------------------------------------------------
echo.
python src\parser.py
set PARSER_EXIT=%ERRORLEVEL%

if not "%PARSER_EXIT%"=="0" (
    echo.
    echo [ОШИБКА] Парсер завершился с кодом %PARSER_EXIT%.
    echo Проверьте лог выше. Если была сетевая ошибка — запустите
    echo скрипт ещё раз, он продолжит с последней страницы.
    echo.
    pause
    exit /b %PARSER_EXIT%
)

echo.
echo [OK] Вакансии собраны в data\vacancies.csv
echo.

REM --- Шаг 2: PDF ---
echo ------------------------------------------------------------
echo   Шаг 2 из 2. Сборка PDF
echo ------------------------------------------------------------
echo.
python src\make_pdfs.py
set PDFS_EXIT=%ERRORLEVEL%

if not "%PDFS_EXIT%"=="0" (
    echo.
    echo [ОШИБКА] Генератор PDF завершился с кодом %PDFS_EXIT%.
    echo Проверьте лог выше.
    echo.
    pause
    exit /b %PDFS_EXIT%
)

echo.
echo ============================================================
echo   Готово.
echo   Файлы в папке output:
echo ============================================================
dir /b "output\*.pdf" 2>nul
echo.

REM --- Открыть папку output в проводнике ---
if exist "output" (
    start "" "output"
)

echo.
pause