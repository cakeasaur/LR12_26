"""Общие фикстуры для тестов."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app
from app.models.user import UserRole
from app.schemas.apartment import ApartmentCreate
from app.schemas.booking import BookingCreate
from app.schemas.review import ReviewCreate
from app.schemas.user import UserCreate
from app.services.apartment_service import create_apartment
from app.services.booking_service import create_booking, update_booking_status
from app.services.review_service import create_review
from app.services.user_service import create_user
from app.models.booking import BookingStatus

# In-memory SQLite для тестов
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Создать таблицы перед тестом, удалить после."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Сессия БД для тестов сервисов."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """TestClient с подменённой БД."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Фикстуры пользователей ──────────────────────────────────────────────────

@pytest.fixture
def tenant(db):
    return create_user(db, UserCreate(
        email="tenant@test.com",
        password="password123",
        full_name="Test Tenant",
        role=UserRole.tenant,
    ))


@pytest.fixture
def landlord(db):
    return create_user(db, UserCreate(
        email="landlord@test.com",
        password="password123",
        full_name="Test Landlord",
        role=UserRole.landlord,
    ))


@pytest.fixture
def admin(db):
    return create_user(db, UserCreate(
        email="admin@test.com",
        password="password123",
        full_name="Test Admin",
        role=UserRole.admin,
    ))


# ── Токены ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_token(client, tenant):
    r = client.post("/api/v1/auth/login", data={
        "username": "tenant@test.com",
        "password": "password123",
    })
    return r.json()["access_token"]


@pytest.fixture
def landlord_token(client, landlord):
    r = client.post("/api/v1/auth/login", data={
        "username": "landlord@test.com",
        "password": "password123",
    })
    return r.json()["access_token"]


@pytest.fixture
def admin_token(client, admin):
    r = client.post("/api/v1/auth/login", data={
        "username": "admin@test.com",
        "password": "password123",
    })
    return r.json()["access_token"]


# ── Квартира ─────────────────────────────────────────────────────────────────

@pytest.fixture
def apartment(db, landlord):
    return create_apartment(db, ApartmentCreate(
        title="Уютная квартира",
        description="Описание",
        address="ул. Пушкина, 1",
        city="Москва",
        price_per_night=2500.0,
        rooms=2,
        max_guests=4,
    ), owner_id=landlord.id)


# ── Бронирование ─────────────────────────────────────────────────────────────

@pytest.fixture
def booking(db, apartment, tenant):
    tomorrow = date.today() + timedelta(days=1)
    day_after = date.today() + timedelta(days=3)
    return create_booking(db, BookingCreate(
        apartment_id=apartment.id,
        check_in=tomorrow,
        check_out=day_after,
    ), tenant_id=tenant.id)


@pytest.fixture
def completed_booking(db, apartment, tenant):
    """Завершённое бронирование — нужно для отзыва."""
    tomorrow = date.today() + timedelta(days=1)
    day_after = date.today() + timedelta(days=3)
    b = create_booking(db, BookingCreate(
        apartment_id=apartment.id,
        check_in=tomorrow,
        check_out=day_after,
    ), tenant_id=tenant.id)
    return update_booking_status(db, b, BookingStatus.completed)
