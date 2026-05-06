from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    price_per_night = Column(Float, nullable=False)
    rooms = Column(Integer, nullable=False)
    max_guests = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="apartments")
    bookings = relationship("Booking", back_populates="apartment")
    reviews = relationship("Review", back_populates="apartment")
