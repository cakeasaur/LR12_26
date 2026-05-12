from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_current_user, require_admin
from app.db.base import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserUpdate, UserCreate
from app.services.user_service import get_user_by_id
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Получить профиль текущего пользователя."""
    return current_user


@router.put("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Обновить профиль текущего пользователя (full_name, phone)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.post("/me/change-password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Изменить пароль текущего пользователя."""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Пароль успешно изменен"}


@router.post("/admin/create", response_model=UserRead)
def admin_create_user(
    data: UserCreate,
    role: str = Query("tenant", pattern="^(tenant|landlord|admin)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    """Создать пользователя с произвольной ролью (только для администратора)."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole(role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[UserRead])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> List[UserRead]:
    """Список всех пользователей (только для администратора)."""
    return db.query(User).offset(skip).limit(limit).all()


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Деактивировать пользователя (только для администратора)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = False
    db.commit()
