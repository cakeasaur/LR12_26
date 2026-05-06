from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_landlord
from app.db.base import get_db
from app.models.user import User
from app.schemas.apartment import ApartmentCreate, ApartmentRead, ApartmentUpdate
from app.services.apartment_service import (
    create_apartment, delete_apartment, get_apartment, get_apartments, update_apartment,
)

router = APIRouter(prefix="/apartments", tags=["apartments"])


@router.get("/", response_model=List[ApartmentRead])
def list_apartments(
    city: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[ApartmentRead]:
    """Список активных объявлений с фильтрацией."""
    return get_apartments(db, city=city, min_price=min_price, max_price=max_price,
                          skip=skip, limit=limit)


@router.get("/{apartment_id}", response_model=ApartmentRead)
def get_one(apartment_id: int, db: Session = Depends(get_db)) -> ApartmentRead:
    """Получить объявление по ID."""
    apt = get_apartment(db, apartment_id)
    if not apt or not apt.is_active:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return apt


@router.post("/", response_model=ApartmentRead, status_code=status.HTTP_201_CREATED)
def create(
    data: ApartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> ApartmentRead:
    """Создать объявление (только для арендодателей)."""
    return create_apartment(db, data, owner_id=current_user.id)


@router.put("/{apartment_id}", response_model=ApartmentRead)
def update(
    apartment_id: int,
    data: ApartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApartmentRead:
    """Обновить объявление (только владелец или админ)."""
    apt = get_apartment(db, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    from app.models.user import UserRole
    if apt.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")
    return update_apartment(db, apt, data)


@router.delete("/{apartment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Удалить объявление (мягкое удаление)."""
    apt = get_apartment(db, apartment_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    from app.models.user import UserRole
    if apt.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")
    delete_apartment(db, apt)
