"""Тесты сервисного слоя (без HTTP)."""
from datetime import date, timedelta

import pytest

from app.models.booking import BookingStatus
from app.models.user import UserRole
from app.schemas.apartment import ApartmentCreate, ApartmentUpdate
from app.schemas.booking import BookingCreate
from app.schemas.payment import PaymentCreate
from app.schemas.review import ReviewCreate
from app.schemas.user import UserCreate
from app.services.apartment_service import (
    create_apartment,
    delete_apartment,
    get_apartment,
    get_apartments,
    update_apartment,
)
from app.services.booking_service import (
    check_availability,
    create_booking,
    get_apartment_bookings,
    get_booking,
    get_user_bookings,
    update_booking_status,
)
from app.services.payment_service import (
    create_payment,
    get_payment_by_booking,
    refund_payment,
    release_payment,
)
from app.services.review_service import (
    create_review,
    delete_review,
    get_apartment_reviews,
    get_review,
    has_completed_booking,
    has_existing_review,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)


# ════════════════════════════════════════════════════════════════════════════
# USER SERVICE
# ════════════════════════════════════════════════════════════════════════════

class TestUserService:
    def test_create_user(self, db):
        user = create_user(db, UserCreate(
            email="u@test.com", password="pass1234",
            full_name="User",
        ))
        assert user.id is not None
        assert user.email == "u@test.com"
        assert user.role == UserRole.tenant
        assert user.is_active is True

    def test_get_by_email_found(self, db, tenant):
        found = get_user_by_email(db, tenant.email)
        assert found is not None
        assert found.id == tenant.id

    def test_get_by_email_not_found(self, db):
        assert get_user_by_email(db, "no@test.com") is None

    def test_get_by_id_found(self, db, tenant):
        found = get_user_by_id(db, tenant.id)
        assert found.email == tenant.email

    def test_get_by_id_not_found(self, db):
        assert get_user_by_id(db, 9999) is None

    def test_authenticate_success(self, db, tenant):
        user = authenticate_user(db, tenant.email, "password123")
        assert user is not None
        assert user.id == tenant.id

    def test_authenticate_wrong_password(self, db, tenant):
        assert authenticate_user(db, tenant.email, "wrongpassword") is None

    def test_authenticate_unknown_email(self, db):
        assert authenticate_user(db, "no@test.com", "password123") is None

    def test_authenticate_inactive_user(self, db, tenant):
        tenant.is_active = False
        db.commit()
        assert authenticate_user(db, tenant.email, "password123") is None

    def test_create_user_with_phone(self, db):
        user = create_user(db, UserCreate(
            email="phone@test.com", password="pass1234",
            full_name="Phone User", phone="+79001234567",
        ))
        assert user.phone == "+79001234567"


# ════════════════════════════════════════════════════════════════════════════
# APARTMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════

class TestApartmentService:
    def _data(self, **kwargs):
        defaults = dict(
            title="Квартира", description=None,
            address="ул. Ленина, 1", city="Москва",
            price_per_night=1000.0, rooms=1, max_guests=2,
        )
        defaults.update(kwargs)
        return ApartmentCreate(**defaults)

    def test_create_apartment(self, db, landlord):
        apt = create_apartment(db, self._data(), owner_id=landlord.id)
        assert apt.id is not None
        assert apt.owner_id == landlord.id
        assert apt.is_active is True

    def test_get_apartment_found(self, db, apartment):
        found = get_apartment(db, apartment.id)
        assert found.id == apartment.id

    def test_get_apartment_not_found(self, db):
        assert get_apartment(db, 9999) is None

    def test_get_apartments_all(self, db, apartment):
        result = get_apartments(db)
        assert len(result) == 1

    def test_get_apartments_filter_city(self, db, landlord):
        create_apartment(db, self._data(city="Москва"), owner_id=landlord.id)
        create_apartment(db, self._data(city="Питер"), owner_id=landlord.id)
        result = get_apartments(db, city="Москва")
        assert all(a.city == "Москва" for a in result)
        assert len(result) == 1

    def test_get_apartments_filter_price(self, db, landlord):
        create_apartment(db, self._data(price_per_night=500.0), owner_id=landlord.id)
        create_apartment(db, self._data(price_per_night=2000.0), owner_id=landlord.id)
        result = get_apartments(db, min_price=1000.0)
        assert all(a.price_per_night >= 1000.0 for a in result)

    def test_get_apartments_filter_max_price(self, db, landlord):
        create_apartment(db, self._data(price_per_night=500.0), owner_id=landlord.id)
        create_apartment(db, self._data(price_per_night=2000.0), owner_id=landlord.id)
        result = get_apartments(db, max_price=1000.0)
        assert all(a.price_per_night <= 1000.0 for a in result)

    def test_get_apartments_inactive_excluded(self, db, apartment):
        apartment.is_active = False
        db.commit()
        result = get_apartments(db)
        assert len(result) == 0

    def test_get_apartments_skip_limit(self, db, landlord):
        for i in range(5):
            create_apartment(db, self._data(title=f"Apt {i}"), owner_id=landlord.id)
        result = get_apartments(db, skip=2, limit=2)
        assert len(result) == 2

    def test_update_apartment(self, db, apartment):
        updated = update_apartment(db, apartment, ApartmentUpdate(title="Новое название"))
        assert updated.title == "Новое название"
        assert updated.city == apartment.city  # остальное не изменилось

    def test_delete_apartment_soft(self, db, apartment):
        delete_apartment(db, apartment)
        found = get_apartment(db, apartment.id)
        assert found.is_active is False


# ════════════════════════════════════════════════════════════════════════════
# BOOKING SERVICE
# ════════════════════════════════════════════════════════════════════════════

class TestBookingService:
    def _dates(self, start_offset=1, end_offset=3):
        return (
            date.today() + timedelta(days=start_offset),
            date.today() + timedelta(days=end_offset),
        )

    def test_create_booking(self, db, apartment, tenant):
        check_in, check_out = self._dates()
        b = create_booking(db, BookingCreate(
            apartment_id=apartment.id, check_in=check_in, check_out=check_out,
        ), tenant_id=tenant.id)
        assert b.id is not None
        assert b.status == BookingStatus.pending
        assert b.tenant_id == tenant.id
        nights = (check_out - check_in).days
        assert b.total_price == apartment.price_per_night * nights

    def test_check_availability_free(self, db, apartment):
        check_in, check_out = self._dates()
        assert check_availability(db, apartment.id, check_in, check_out) is True

    def test_check_availability_conflict(self, db, apartment, tenant):
        check_in, check_out = self._dates(1, 5)
        create_booking(db, BookingCreate(
            apartment_id=apartment.id, check_in=check_in, check_out=check_out,
        ), tenant_id=tenant.id)
        # Пересекающийся период
        assert check_availability(
            db, apartment.id,
            date.today() + timedelta(days=2),
            date.today() + timedelta(days=4),
        ) is False

    def test_check_availability_exclude_booking(self, db, apartment, tenant):
        check_in, check_out = self._dates(1, 5)
        b = create_booking(db, BookingCreate(
            apartment_id=apartment.id, check_in=check_in, check_out=check_out,
        ), tenant_id=tenant.id)
        # Исключаем саму бронь — должно быть свободно
        assert check_availability(
            db, apartment.id, check_in, check_out, exclude_booking_id=b.id
        ) is True

    def test_get_booking_found(self, db, booking):
        found = get_booking(db, booking.id)
        assert found.id == booking.id

    def test_get_booking_not_found(self, db):
        assert get_booking(db, 9999) is None

    def test_get_user_bookings(self, db, booking, tenant):
        result = get_user_bookings(db, tenant.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant.id

    def test_get_apartment_bookings(self, db, booking, apartment):
        result = get_apartment_bookings(db, apartment.id)
        assert len(result) == 1

    def test_update_booking_status(self, db, booking):
        updated = update_booking_status(db, booking, BookingStatus.confirmed)
        assert updated.status == BookingStatus.confirmed


# ════════════════════════════════════════════════════════════════════════════
# PAYMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════

class TestPaymentService:
    def test_create_payment(self, db, booking):
        payment = create_payment(db, PaymentCreate(
            booking_id=booking.id, transaction_ref="TXN-001",
        ), amount=booking.total_price)
        assert payment.id is not None
        assert payment.booking_id == booking.id
        assert payment.amount == booking.total_price

    def test_get_payment_by_booking(self, db, booking):
        create_payment(db, PaymentCreate(
            booking_id=booking.id, transaction_ref="TXN-001",
        ), amount=booking.total_price)
        p = get_payment_by_booking(db, booking.id)
        assert p is not None
        assert p.booking_id == booking.id

    def test_get_payment_by_booking_not_found(self, db):
        assert get_payment_by_booking(db, 9999) is None

    def test_release_payment(self, db, booking):
        from app.models.payment import PaymentStatus
        p = create_payment(db, PaymentCreate(
            booking_id=booking.id, transaction_ref="TXN-002",
        ), amount=booking.total_price)
        released = release_payment(db, p)
        assert released.status == PaymentStatus.released

    def test_refund_payment(self, db, booking):
        from app.models.payment import PaymentStatus
        p = create_payment(db, PaymentCreate(
            booking_id=booking.id, transaction_ref="TXN-003",
        ), amount=booking.total_price)
        refunded = refund_payment(db, p)
        assert refunded.status == PaymentStatus.refunded


# ════════════════════════════════════════════════════════════════════════════
# REVIEW SERVICE
# ════════════════════════════════════════════════════════════════════════════

class TestReviewService:
    def test_has_completed_booking_true(self, db, completed_booking, tenant, apartment):
        assert has_completed_booking(db, tenant.id, apartment.id) is True

    def test_has_completed_booking_false(self, db, tenant, apartment):
        assert has_completed_booking(db, tenant.id, apartment.id) is False

    def test_has_existing_review_false(self, db, tenant, apartment):
        assert has_existing_review(db, tenant.id, apartment.id) is False

    def test_create_review(self, db, completed_booking, tenant, apartment):
        r = create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=5, comment="Отлично!",
        ), author_id=tenant.id)
        assert r.id is not None
        assert r.rating == 5

    def test_create_duplicate_review_raises(self, db, completed_booking, tenant, apartment):
        create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=4, comment="Хорошо",
        ), author_id=tenant.id)
        with pytest.raises(ValueError, match="уже оставили отзыв"):
            create_review(db, ReviewCreate(
                apartment_id=apartment.id, rating=3, comment="Снова",
            ), author_id=tenant.id)

    def test_has_existing_review_true(self, db, completed_booking, tenant, apartment):
        create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=5, comment="Супер",
        ), author_id=tenant.id)
        assert has_existing_review(db, tenant.id, apartment.id) is True

    def test_get_apartment_reviews(self, db, completed_booking, tenant, apartment):
        create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=5, comment="Отлично",
        ), author_id=tenant.id)
        reviews = get_apartment_reviews(db, apartment.id)
        assert len(reviews) == 1

    def test_get_review_found(self, db, completed_booking, tenant, apartment):
        r = create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=4, comment="Хорошо",
        ), author_id=tenant.id)
        found = get_review(db, r.id)
        assert found.id == r.id

    def test_get_review_not_found(self, db):
        assert get_review(db, 9999) is None

    def test_delete_review(self, db, completed_booking, tenant, apartment):
        r = create_review(db, ReviewCreate(
            apartment_id=apartment.id, rating=3, comment="Норм",
        ), author_id=tenant.id)
        delete_review(db, r)
        assert get_review(db, r.id) is None
