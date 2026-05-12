# Лабораторная работа №12 — Сервис аренды квартир

**Студент:** Кипчатов Максим Маратович  
**Группа:** 221331  
**Вариант:** 26 — Сервис аренды квартир (повышенный уровень)

---

## Описание

Веб-приложение для поиска и бронирования квартир. Реализовано на FastAPI с Jinja2-шаблонами и REST API. Поддерживает три роли пользователей: арендатор, арендодатель и администратор.

## Стек технологий

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Jinja2, Bootstrap 5
- **Auth:** JWT (python-jose), bcrypt
- **Тесты:** pytest, coverage.py
- **CI/CD:** GitHub Actions

## Функциональность

### Роли пользователей
| Роль | Возможности |
|---|---|
| `tenant` | Поиск квартир, бронирование, оплата, отзывы |
| `landlord` | Публикация объявлений, управление бронями |
| `admin` | Полный доступ + панель управления пользователями |

### Основные возможности
- Регистрация и вход по email/паролю
- Поиск квартир с фильтрацией по городу и цене
- Бронирование с проверкой доступности дат
- Эскроу-оплата (заморозка → перевод / возврат)
- Отзывы только после завершённого проживания
- Административная панель

## Установка и запуск

```bash
# Клонировать репозиторий
git clone https://github.com/cakeasaur/LR12_26.git
cd LR12_26

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python -m uvicorn app.main:app --port 8000
```

Приложение будет доступно по адресу: http://localhost:8000

API-документация: http://localhost:8000/docs

## Структура проекта

```
app/
├── api/v1/endpoints/   # REST API: auth, users, apartments, bookings, payments, reviews
├── core/               # Конфигурация, безопасность (JWT, bcrypt)
├── db/                 # SQLAlchemy engine, сессия
├── models/             # ORM-модели: User, Apartment, Booking, Payment, Review
├── schemas/            # Pydantic-схемы
├── services/           # Бизнес-логика
└── web/                # Jinja2 веб-интерфейс
templates/              # HTML-шаблоны (Bootstrap 5)
tests/                  # Unit-тесты
docs/                   # Отчёты по заданиям
```

## Тесты

```bash
# Запустить тесты
python -m pytest tests/ -v

# С отчётом покрытия
python -m pytest tests/ --cov=app --cov-config=.coveragerc --cov-report=term-missing
```

**Результат:** 136 тестов, покрытие **98%**

## Выполненные задания

| № | Задание | Статус | Отчёт |
|---|---|---|---|
| 1 | Веб-приложение (FastAPI + Jinja2 UI) | ✅ | — |
| 2 | Code review (5 найденных и исправленных багов) | ✅ | `docs/code_review.md` |
| 3 | Настройка локальной LLM (Ollama + qwen3.5:27b) | ✅ | `docs/llm_comparison.md` |
| 4 | CI/CD GitHub Actions (AI-анализ PR) | ✅ | `.github/workflows/ai-pr-review.yml` |
| 6 | Сравнение 3 или более ИИ-моделей (Claude, GPT-4, Qwen) | ✅ | `docs/model_comparison_task6.md` |
| 7 | Unit-тесты, покрытие ≥ 90% | ✅ | `docs/testing_report.md` |

