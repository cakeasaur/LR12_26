from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.apartment import Apartment
from app.schemas.booking import BookingCreate

_VALID_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.pending:   {BookingStatus.confirmed, BookingStatus.cancelled},
    BookingStatus.confirmed: {BookingStatus.completed, BookingStatus.cancelled},
    BookingStatus.completed: set(),
    BookingStatus.cancelled: set(),
}


class BookingConflictError(Exception):
    """Поднимается, когда даты бронирования пересекаются с другой активной бронью."""


def check_availability(
    db: Session, apartment_id: int, check_in: date, check_out: date,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """Проверяет, нет ли пересечений с существующими бронями."""
    query = db.query(Booking).filter(
        Booking.apartment_id == apartment_id,
        Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.first() is None


def create_booking(db: Session, data: BookingCreate, tenant_id: int) -> Booking:
    apartment = db.query(Apartment).filter(Apartment.id == data.apartment_id).first()
    if not apartment:
        raise ValueError(f"Квартира {data.apartment_id} не найдена")
    nights = (data.check_out - data.check_in).days
    total_price = apartment.price_per_night * nights

    booking = Booking(
        apartment_id=data.apartment_id,
        tenant_id=tenant_id,
        check_in=data.check_in,
        check_out=data.check_out,
        total_price=total_price,
        status=BookingStatus.pending,
    )
    db.add(booking)
    db.flush()  # получаем id, не коммитя — для повторной проверки в той же транзакции

    # TOCTOU-mitigation: между check_availability в endpoint и этим INSERT
    # параллельный запрос мог успеть вставить пересекающуюся бронь.
    # Перепроверяем уже после своего flush, исключая собственную запись.
    if not check_availability(
        db, data.apartment_id, data.check_in, data.check_out,
        exclude_booking_id=booking.id,
    ):
        db.rollback()
        raise BookingConflictError("Квартира недоступна на выбранные даты")

    db.commit()
    db.refresh(booking)
    return booking


def get_booking(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_user_bookings(db: Session, tenant_id: int, skip: int = 0, limit: int = 20) -> List[Booking]:
    return db.query(Booking).filter(Booking.tenant_id == tenant_id).offset(skip).limit(limit).all()


def get_apartment_bookings(db: Session, apartment_id: int) -> List[Booking]:
    return db.query(Booking).filter(Booking.apartment_id == apartment_id).all()


def update_booking_status(
    db: Session, booking: Booking, status: BookingStatus
) -> Booking:
    allowed = _VALID_TRANSITIONS.get(booking.status, set())
    if status not in allowed:
        raise ValueError(
            f"Переход {booking.status.value!r} → {status.value!r} недопустим"
        )
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking
