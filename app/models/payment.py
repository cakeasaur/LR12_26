from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    held = "held"           # заморожено (эскроу)
    released = "released"   # переведено арендодателю
    refunded = "refunded"   # возвращено арендатору


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.held, nullable=False)
    # В реальной системе здесь был бы токен платёжной системы
    transaction_ref = Column(String(100), nullable=True)

    booking = relationship("Booking", back_populates="payment")
