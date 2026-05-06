from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User, UserRole
from app.schemas.review import ReviewCreate, ReviewRead
from app.services.review_service import (
    create_review, delete_review, get_apartment_reviews,
    get_review, has_completed_booking,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/apartments/{apartment_id}", response_model=List[ReviewRead])
def list_reviews(
    apartment_id: int,
    db: Session = Depends(get_db),
) -> List[ReviewRead]:
    """Список отзывов для квартиры."""
    return get_apartment_reviews(db, apartment_id)


@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewRead:
    """Оставить отзыв (только после завершённого бронирования)."""
    if not has_completed_booking(db, current_user.id, data.apartment_id):
        raise HTTPException(
            status_code=403,
            detail="Отзыв можно оставить только после завершённого проживания",
        )
    return create_review(db, data, author_id=current_user.id)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Удалить отзыв (автор или админ)."""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    if review.author_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")
    delete_review(db, review)
