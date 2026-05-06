# Задание 2 — Code Review сгенерированного кода

**Проект:** Сервис аренды квартир (Вариант 26)  
**Инструмент генерации:** Claude (Anthropic)  
**Найдено и исправлено:** 5 ошибок

---

## Ошибка 1 — Несовместимость passlib с bcrypt 5.x

### Что сгенерировал ИИ

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### В чём проблема

`passlib` — популярная обёртка над алгоритмами хеширования, которую ИИ использует по умолчанию. Однако библиотека давно не обновлялась и несовместима с `bcrypt >= 4.0`. При попытке зарегистрироваться пользователь получал ошибку прямо в UI:

```
password cannot be longer than 72 bytes, truncate manually if necessary
```

Кроме того, bcrypt имеет жёсткий лимит в 72 байта на пароль, о котором ИИ не предупредил — длинные пароли молча обрезались бы, что является уязвимостью безопасности.

### Как исправил

Убрал `passlib`, перешёл на прямое использование `bcrypt`. Добавил SHA-256 предхеширование: пароль любой длины сначала хешируется в 32-байтный дайджест, который bcrypt никогда не обрежет.

```python
# app/core/security.py
import hashlib
import bcrypt

def _prehash(password: str) -> bytes:
    """SHA-256 → 32 байта. Bcrypt-лимит 72 байта никогда не достигается."""
    return hashlib.sha256(password.encode()).digest()

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode())
```

**Коммит:** `fix: заменить passlib на bcrypt напрямую, добавить SHA-256 предхеширование`

---

## Ошибка 2 — JWT: поле `sub` передавалось как integer

### Что сгенерировал ИИ

```python
# app/api/v1/endpoints/auth.py и app/web/router.py
access_token = create_access_token(data={"sub": user.id})  # user.id — int

# app/api/deps.py и app/web/router.py
user_id = payload.get("sub")  # возвращался int, но JWT ждёт строку
```

### В чём проблема

Стандарт JWT (RFC 7519) требует, чтобы поле `sub` было строкой. Библиотека `python-jose` строго следует стандарту и при декодировании выбрасывает исключение:

```
JWTClaimsError: Subject must be a string.
```

В результате `decode_access_token` всегда возвращал `None`, кука не читалась, и каждый вход в систему заканчивался молчаливым редиректом на главную — без какого-либо сообщения об ошибке.

### Как исправил

При создании токена `user.id` приводится к строке, при чтении — обратно к `int`.

```python
# Создание токена
access_token = create_access_token(data={"sub": str(user.id)})

# Чтение токена
user_id = int(payload.get("sub"))
```

**Коммит:** `fix: JWT sub передавать как строку, декодировать в int`

---

## Ошибка 3 — Starlette 1.0: изменился API Jinja2Templates

### Что сгенерировал ИИ

```python
# app/web/router.py — старый API (Starlette < 0.38)
templates = Jinja2Templates(directory="templates")

return templates.TemplateResponse("index.html", {
    "request": request,
    "apartments": apartments,
})
```

### В чём проблема

В Starlette 1.0 сигнатура `TemplateResponse` изменилась: `request` теперь передаётся первым позиционным аргументом, а не внутри словаря контекста. ИИ сгенерировал код под старую версию API, что приводило к ошибке 500 на всех страницах:

```
AttributeError: 'dict' object has no attribute 'split'
```

Ошибка возникала потому, что Jinja2 получал словарь там, где ожидал строку с именем шаблона.

### Как исправил

Обновил все вызовы `TemplateResponse` под новый API и убрал `request` из словаря контекста.

```python
# Новый API (Starlette >= 1.0)
return templates.TemplateResponse(request, "index.html", {
    "apartments": apartments,
})
```

**Коммит:** `fix: обновить TemplateResponse под Starlette 1.0 API`

---

## Ошибка 4 — Заблокированный пользователь мог войти в систему

### Что сгенерировал ИИ

```python
# app/services/user_service.py
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
```

### В чём проблема

Функция проверяет только существование пользователя и правильность пароля, но игнорирует флаг `is_active`. Администратор может заблокировать пользователя через панель управления (`is_active = False`), однако тот без проблем продолжит входить в систему — блокировка не имеет никакого эффекта.

### Как исправил

Добавил проверку `user.is_active` в условие аутентификации.

```python
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user
```

**Коммит:** `fix: заблокированный пользователь не может войти в систему`

---

## Ошибка 5 — Один пользователь мог оставить несколько отзывов

### Что сгенерировал ИИ

```python
# app/services/review_service.py
def create_review(db: Session, data: ReviewCreate, author_id: int) -> Review:
    review = Review(
        apartment_id=data.apartment_id,
        author_id=author_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
```

### В чём проблема

Сервисный слой не проверяет уникальность отзыва. Через прямые запросы к API (`POST /api/v1/reviews`) один пользователь мог оставить неограниченное количество отзывов на одну квартиру, искусственно накручивая или занижая рейтинг. UI блокировал это визуально, но защиты на уровне бизнес-логики не было.

### Как исправил

Добавил функцию `has_existing_review` и проверку в `create_review` на уровне сервиса — это единственное надёжное место, которое защищает как API, так и любые будущие интерфейсы.

```python
def has_existing_review(db: Session, author_id: int, apartment_id: int) -> bool:
    return db.query(Review).filter(
        Review.author_id == author_id,
        Review.apartment_id == apartment_id,
    ).first() is not None


def create_review(db: Session, data: ReviewCreate, author_id: int) -> Review:
    if has_existing_review(db, author_id, data.apartment_id):
        raise ValueError("Вы уже оставили отзыв на эту квартиру")
    # ... создание отзыва
```

**Коммит:** `fix: запретить дублирующиеся отзывы от одного пользователя`

---

## Итоговая таблица

| # | Файл | Тип ошибки | Критичность |
|---|------|------------|-------------|
| 1 | `app/core/security.py` | Несовместимость зависимостей | 🔴 Высокая |
| 2 | `app/api/`, `app/web/router.py` | Нарушение стандарта JWT | 🔴 Высокая |
| 3 | `app/web/router.py` | Устаревший API библиотеки | 🟡 Средняя |
| 4 | `app/services/user_service.py` | Логическая ошибка (безопасность) | 🔴 Высокая |
| 5 | `app/services/review_service.py` | Отсутствие валидации бизнес-правила | 🟡 Средняя |

---

## Выводы

ИИ генерирует рабочий код, но допускает характерные ошибки:

1. **Устаревшие зависимости** — ИИ обучен на исторических данных и предпочитает проверенные, но устаревшие библиотеки (`passlib`).
2. **Игнорирование версий** — сгенерированный код не учитывает breaking changes в новых версиях (`Starlette 1.0`, `python-jose`).
3. **Неполная бизнес-логика** — ИИ реализует «счастливый путь», упуская граничные случаи (заблокированные пользователи, дублирующиеся записи).

Вывод: код ИИ требует обязательного code review, особенно в части безопасности и совместимости зависимостей.
