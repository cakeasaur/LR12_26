from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        UniqueConstraint("author_id", "apartment_id", name="uq_review_author_apartment"),
    )

    apartment = relationship("Apartment", back_populates="reviews")
    author = relationship("User", back_populates="reviews")
