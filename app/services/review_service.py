from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.booking import Booking, BookingStatus
from app.schemas.review import ReviewCreate


def has_completed_booking(db: Session, user_id: int, apartment_id: int) -> bool:
    """Оставить отзыв можно только после завершённой брони."""
    return db.query(Booking).filter(
        Booking.tenant_id == user_id,
        Booking.apartment_id == apartment_id,
        Booking.status == BookingStatus.completed,
    ).first() is not None


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


def get_apartment_reviews(db: Session, apartment_id: int) -> List[Review]:
    return db.query(Review).filter(Review.apartment_id == apartment_id).all()


def get_review(db: Session, review_id: int) -> Optional[Review]:
    return db.query(Review).filter(Review.id == review_id).first()


def delete_review(db: Session, review: Review) -> None:
    db.delete(review)
    db.commit()
