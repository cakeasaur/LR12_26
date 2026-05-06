# Задание 3 — Настройка локальной LLM и сравнение с облачным решением

## Окружение

| | Локальная модель | Облачная модель |
|---|---|---|
| **Модель** | Qwen3.5:27b | Claude Sonnet (Anthropic) |
| **Запуск** | Ollama 0.21.1, localhost:11434 | Claude Code (API) |
| **Автодополнение** | Continue.dev v1.2.22 в VS Code | Claude Code встроен |
| **Железо** | Локальный ПК пользователя | Облачные серверы Anthropic |

### Установка и настройка

Ollama был уже установлен. Для подключения к VS Code:

```bash
code --install-extension Continue.continue
```

Конфиг `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen 3.5 27B (Local)",
      "provider": "ollama",
      "model": "qwen3.5:27b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen 3.5 27B Autocomplete",
    "provider": "ollama",
    "model": "qwen3.5:27b",
    "apiBase": "http://localhost:11434"
  }
}
```

> **Примечание:** Qwen3.5 по умолчанию использует режим «размышления» (`<think>`), который съедает весь лимит токенов, не выдавая ответа. Решение — передавать параметр `"think": false` в запросе к Ollama API.

---

## Задача 1 — CRUD: поиск свободных квартир

**Промпт:** написать функцию `get_available_apartments(db, city, check_in, check_out)` на SQLAlchemy, возвращающую квартиры без пересекающихся бронирований.

### Qwen3.5:27b (локальная) — 98.4 сек

```python
from sqlalchemy import and_, or_

def get_available_apartments(db, city: str, check_in, check_out):
    return db.query(Apartment).filter(
        Apartment.city == city,
        ~db.query(Booking).filter(
            Booking.apartment_id == Apartment.id,
            Booking.status.in_(['confirmed', 'pending']),
            or_(
                and_(Booking.check_in <= check_in, Booking.check_out >= check_in),
                and_(Booking.check_in <= check_out, Booking.check_out >= check_out),
                and_(Booking.check_in >= check_in, Booking.check_out <= check_out),
            )
        ).exists()
    ).all()
```

**Оценка:** ✅ Логика пересечения дат корректна, использует `.exists()` — оптимально. Код рабочий.

### Claude Sonnet (облачная)

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_, exists
from datetime import date

def get_available_apartments(
    db: Session,
    city: str,
    check_in: date,
    check_out: date,
) -> list[Apartment]:
    busy = db.query(Booking.apartment_id).filter(
        Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    ).subquery()

    return db.query(Apartment).filter(
        Apartment.city.ilike(f"%{city}%"),
        Apartment.is_active == True,
        Apartment.id.notin_(busy),
    ).all()
```

**Оценка:** ✅ Добавлены type hints, фильтр `is_active`, поиск без учёта регистра (`ilike`), использует enum вместо строк.

---

## Задача 2 — SQL: топ-5 квартир по завершённым бронированиям

**Промпт:** SQL-запрос — топ-5 квартир по количеству завершённых бронирований за последние 30 дней.

### Qwen3.5:27b (локальная) — 66.9 сек

```sql
SELECT
    a.title,
    a.city,
    COUNT(b.id) AS booking_count
FROM apartments a
JOIN bookings b ON a.id = b.apartment_id
WHERE
    b.status = 'completed'
    AND b.check_out >= DATE('now', '-30 days')
GROUP BY a.id, a.title, a.city
ORDER BY booking_count DESC
LIMIT 5;
```

**Оценка:** ✅ Корректный запрос. Использует `DATE('now', '-30 days')` — SQLite-синтаксис.

### Claude Sonnet (облачная)

```sql
SELECT
    a.id,
    a.title,
    a.city,
    COUNT(b.id) AS completed_bookings
FROM apartments a
JOIN bookings b ON b.apartment_id = a.id
WHERE
    b.status = 'completed'
    AND b.check_out >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY a.id, a.title, a.city
ORDER BY completed_bookings DESC
LIMIT 5;
```

**Оценка:** ✅ Включает `a.id`, использует стандартный SQL `INTERVAL` (PostgreSQL-совместимый).

---

## Задача 3 — Regex: валидация российского телефона

**Промпт:** функция `validate_phone(phone: str) -> bool` для формата `+7XXXXXXXXXX`.

### Qwen3.5:27b (локальная) — 31.6 сек

```python
import re

def validate_phone(phone: str) -> bool:
    pattern = r'^\+7\d{10}$'
    return bool(re.match(pattern, phone))
```

**Оценка:** ✅ Корректно и лаконично. Полностью рабочий код.

### Claude Sonnet (облачная)

```python
import re

_PHONE_RE = re.compile(r'^\+7\d{10}$')

def validate_phone(phone: str) -> bool:
    """Проверяет российский номер телефона: +7XXXXXXXXXX (11 цифр)."""
    return bool(_PHONE_RE.match(phone))
```

**Оценка:** ✅ Скомпилированный паттерн (быстрее при многократном вызове), добавлен docstring.

---

## Итоговая таблица сравнения

| Критерий | Qwen3.5:27b (локальная) | Claude Sonnet (облачная) |
|---|---|---|
| **Задача 1 — скорость** | 98.4 сек | ~3 сек |
| **Задача 2 — скорость** | 66.9 сек | ~2 сек |
| **Задача 3 — скорость** | 31.6 сек | ~1 сек |
| **Средняя скорость** | ~65 сек | ~2 сек |
| **Корректность кода** | ✅ Высокая | ✅ Высокая |
| **Качество кода** | Хорошее (без type hints) | Отличное (type hints, docstring, enum) |
| **Релевантность** | Средняя (общий код) | Высокая (учитывает контекст проекта) |
| **Приватность данных** | ✅ Полная (всё локально) | ❌ Данные уходят в облако |
| **Стоимость** | Бесплатно после скачивания | Платная подписка / API |
| **Требования к железу** | 17 GB RAM/VRAM | Не нужно |
| **Автодополнение в IDE** | ✅ Continue.dev | ✅ Claude Code |

---

## Выводы

**Качество:** обе модели справились со всеми тремя задачами корректно. Облачная модель выдаёт более «продакшн-готовый» код: type hints, docstrings, enum вместо строк, учёт контекста проекта.

**Скорость:** облачная модель быстрее в ~30 раз. Для интерактивного автодополнения локальная модель подходит слабо — задержка 30–100 сек неприемлема.

**Где локальная LLM выигрывает:**
- Работа с конфиденциальными данными (код не покидает машину)
- Офлайн-разработка
- Нет расходов на API

**Итог:** для учебных и коммерческих проектов без строгих требований к конфиденциальности облачные решения предпочтительнее по скорости и качеству. Локальная LLM — разумный выбор при работе с чувствительными данными или ограниченном бюджете.
