from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.base import get_db
from app.models.booking import BookingStatus
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingRead, BookingStatusUpdate
from app.services.apartment_service import get_apartment
from app.services.booking_service import (
    BookingConflictError, check_availability, create_booking, get_booking,
    get_user_bookings, update_booking_status,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingRead:
    """Создать бронирование."""
    apt = get_apartment(db, data.apartment_id)
    if not apt or not apt.is_active:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if not check_availability(db, data.apartment_id, data.check_in, data.check_out):
        raise HTTPException(status_code=409, detail="Квартира недоступна на выбранные даты")
    try:
        return create_booking(db, data, tenant_id=current_user.id)
    except BookingConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/my", response_model=List[BookingRead])
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[BookingRead]:
    """Список бронирований текущего пользователя."""
    return get_user_bookings(db, tenant_id=current_user.id)


@router.get("/{booking_id}", response_model=BookingRead)
def get_one(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingRead:
    """Получить бронирование по ID."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    apt = get_apartment(db, booking.apartment_id)
    is_tenant = booking.tenant_id == current_user.id
    is_landlord = apt and apt.owner_id == current_user.id
    if not is_tenant and not is_landlord and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет доступа")
    return booking


@router.patch("/{booking_id}/status", response_model=BookingRead)
def update_status(
    booking_id: int,
    data: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingRead:
    """Изменить статус бронирования."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    apt = get_apartment(db, booking.apartment_id)

    # Арендатор может только отменить свою бронь
    if booking.tenant_id == current_user.id:
        if data.status != BookingStatus.cancelled:
            raise HTTPException(status_code=403, detail="Арендатор может только отменить бронь")
    # Арендодатель может подтвердить, отменить или завершить
    elif apt and apt.owner_id == current_user.id:
        pass
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет прав на изменение статуса")

    return update_booking_status(db, booking, data.status)
