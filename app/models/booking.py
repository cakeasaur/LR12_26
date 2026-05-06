from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class BookingStatus(str, enum.Enum):
    pending = "pending"       # ожидает подтверждения
    confirmed = "confirmed"   # подтверждено
    cancelled = "cancelled"   # отменено
    completed = "completed"   # завершено


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending, nullable=False)

    apartment = relationship("Apartment", back_populates="bookings")
    tenant = relationship("User", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False)
