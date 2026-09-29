#!/usr/bin/env bash
# ============================================================
#   Парсер вакансий и генератор PDF
#   Региональный кадровый центр Краснодарского края
# ============================================================

set -e

cd "$(dirname "$0")"

# --- Цвета (если терминал поддерживает) ---
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[0;33m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; BOLD=''; NC=''
fi

echo "============================================================"
echo "  Парсер вакансий и генератор PDF"
echo "  Региональный кадровый центр Краснодарского края"
echo "============================================================"
echo

# --- Проверка venv ---
if [ ! -f ".venv/bin/activate" ]; then
    echo -e "${RED}[ОШИБКА] Виртуальное окружение .venv не найдено.${NC}"
    echo
    echo "Создайте его командами:"
    echo "    python3 -m venv .venv"
    echo "    source .venv/bin/activate"
    echo "    pip install -r requirements.txt"
    echo
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# --- Шаг 1: парсер ---
echo "------------------------------------------------------------"
echo "  Шаг 1 из 2. Сбор вакансий с сайта"
echo "------------------------------------------------------------"
echo
if ! python src/parser.py; then
    echo
    echo -e "${RED}[ОШИБКА] Парсер завершился с ошибкой.${NC}"
    echo "Проверьте лог выше. Если была сетевая ошибка —"
    echo "запустите скрипт ещё раз, он продолжит с последней страницы."
    echo
    exit 1
fi
echo
echo -e "${GREEN}[OK] Вакансии собраны в data/vacancies.csv${NC}"
echo

# --- Шаг 2: PDF ---
echo "------------------------------------------------------------"
echo "  Шаг 2 из 2. Сборка PDF"
echo "------------------------------------------------------------"
echo
if ! python src/make_pdfs.py; then
    echo
    echo -e "${RED}[ОШИБКА] Генератор PDF завершился с ошибкой.${NC}"
    echo "Проверьте лог выше."
    echo
    exit 1
fi

echo
echo "============================================================"
echo "  Готово."
echo "  Файлы в папке output:"
echo "============================================================"
ls -lh output/*.pdf 2>/dev/null || echo "  (PDF не найдены)"
echo

# --- Открыть папку output ---
if [ -d "output" ]; then
    if command -v xdg-open >/dev/null 2>&1; then
        # Linux
        read -r -p "Открыть папку output? [y/N] " ans
        case "$ans" in
            [Yy]*) xdg-open output >/dev/null 2>&1 & ;;
        esac
    elif command -v open >/dev/null 2>&1; then
        # macOS
        read -r -p "Открыть папку output? [y/N] " ans
        case "$ans" in
            [Yy]*) open output ;;
        esac
    fi
fi