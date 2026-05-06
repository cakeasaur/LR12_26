from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.booking import BookingStatus
from app.models.user import User, UserRole
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services.booking_service import get_booking, update_booking_status
from app.services.apartment_service import get_apartment
from app.services.payment_service import (
    create_payment, get_payment_by_booking, refund_payment, release_payment,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def pay_booking(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    """Оплатить бронирование (заморозить средства в эскроу)."""
    booking = get_booking(db, data.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    if booking.tenant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    if get_payment_by_booking(db, data.booking_id):
        raise HTTPException(status_code=409, detail="Бронирование уже оплачено")
    payment = create_payment(db, data, amount=booking.total_price)
    update_booking_status(db, booking, BookingStatus.confirmed)
    return payment


@router.get("/{booking_id}", response_model=PaymentRead)
def get_payment(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    """Получить информацию об оплате бронирования."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    payment = get_payment_by_booking(db, booking_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    apt = get_apartment(db, booking.apartment_id)
    is_tenant = booking.tenant_id == current_user.id
    is_landlord = apt and apt.owner_id == current_user.id
    if not is_tenant and not is_landlord and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет доступа")
    return payment


@router.post("/{booking_id}/release", response_model=PaymentRead)
def release(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    """Перевести средства арендодателю после завершения аренды."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    apt = get_apartment(db, booking.apartment_id)
    if not apt or apt.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет доступа")
    payment = get_payment_by_booking(db, booking_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    update_booking_status(db, booking, BookingStatus.completed)
    return release_payment(db, payment)


@router.post("/{booking_id}/refund", response_model=PaymentRead)
def refund(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    """Вернуть средства арендатору при отмене."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    if booking.status != BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Бронирование не отменено")
    payment = get_payment_by_booking(db, booking_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    apt = get_apartment(db, booking.apartment_id)
    is_tenant = booking.tenant_id == current_user.id
    is_landlord = apt and apt.owner_id == current_user.id
    if not is_tenant and not is_landlord and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет доступа")
    return refund_payment(db, payment)
