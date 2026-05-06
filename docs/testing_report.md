# Задание 7 — Unit-тесты и покрытие кода

## Инструменты

| Инструмент | Версия | Назначение |
|---|---|---|
| `pytest` | 8.4.2 | Тест-раннер |
| `pytest-cov` | 7.1.0 | Сбор покрытия |
| `coverage.py` | 7.6.0 | Анализ покрытия |
| `httpx` | 0.27+ | HTTP-клиент для API-тестов |
| SQLite in-memory | — | Изолированная БД для тестов |

## Структура тестов

```
tests/
├── conftest.py                          # Фикстуры (DB, users, apartments, bookings)
├── test_security.py                     # app/core/security.py
├── test_services.py                     # Все сервисы (user, apartment, booking, payment, review)
├── test_api_auth.py                     # POST /auth/register, /auth/login
├── test_api_apartments.py               # GET/POST/PUT/DELETE /apartments/
├── test_api_bookings.py                 # GET/POST/PATCH /bookings/
└── test_api_payments_reviews_users.py   # /payments/, /reviews/, /users/
```

## Запуск

```bash
# Запустить тесты
python -m pytest tests/ -v

# С отчётом покрытия в терминале
python -m pytest tests/ --cov=app --cov-config=.coveragerc --cov-report=term-missing

# HTML-отчёт
python -m pytest tests/ --cov=app --cov-config=.coveragerc --cov-report=html:docs/coverage_html
```

## Результаты

```
136 passed, 0 failed
```

## Покрытие по модулям

| Модуль | Строк | Покрыто | % |
|---|---|---|---|
| `app/core/security.py` | 22 | 22 | **100%** |
| `app/core/config.py` | 9 | 9 | **100%** |
| `app/services/user_service.py` | 20 | 20 | **100%** |
| `app/services/apartment_service.py` | 30 | 30 | **100%** |
| `app/services/booking_service.py` | 31 | 31 | **100%** |
| `app/services/payment_service.py` | 23 | 23 | **100%** |
| `app/services/review_service.py` | 24 | 24 | **100%** |
| `app/api/v1/endpoints/auth.py` | 20 | 20 | **100%** |
| `app/api/v1/endpoints/apartments.py` | 39 | 39 | **100%** |
| `app/api/v1/endpoints/reviews.py` | 25 | 25 | **100%** |
| `app/api/v1/endpoints/users.py` | 29 | 29 | **100%** |
| `app/api/v1/endpoints/payments.py` | 66 | 64 | 97% |
| `app/api/v1/endpoints/bookings.py` | 47 | 45 | 96% |
| `app/api/deps.py` | 24 | 23 | 96% |
| `app/main.py` | 13 | 12 | 92% |
| `app/schemas/*` | 81 | 78 | 96% |
| **ИТОГО** | **524** | **511** | **98%** |

> `app/web/router.py` и `app/models/*` исключены из подсчёта (Jinja2 UI и декларативные модели).

## Что тестируется

### Security
- Хэширование паролей (bcrypt + SHA-256 предхэш)
- Верификация правильного/неправильного пароля
- Длинные пароли > 72 байт (защита от bcrypt truncation)
- Юникод-пароли
- Создание и декодирование JWT
- Невалидные токены

### Сервисы
- CRUD пользователей: создание, поиск по email/id, аутентификация
- Блокировка неактивных пользователей
- CRUD квартир: создание, фильтрация (город, цена), пагинация, мягкое удаление
- Бронирования: создание, проверка доступности (конфликт дат, exclude_booking_id)
- Платежи: создание, release, refund
- Отзывы: создание, дедупликация, удаление

### API endpoints
- Регистрация: успех, дубль email, короткий пароль
- Вход: успех, неверный пароль, неактивный пользователь
- Квартиры: все CRUD + права доступа (tenant/landlord/admin)
- Бронирования: создание с конфликтом дат, смена статуса по ролям
- Платежи: оплата, release, refund + граничные случаи
- Отзывы: создание только после завершённой брони, удаление
- Пользователи: профиль, обновление, admin-операции
