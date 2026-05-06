from sqlalchemy import Boolean, Column, Integer, String, Enum
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    tenant = "tenant"       # арендатор
    landlord = "landlord"   # арендодатель
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.tenant, nullable=False)
    is_active = Column(Boolean, default=True)

    apartments = relationship("Apartment", back_populates="owner")
    bookings = relationship("Booking", back_populates="tenant")
    reviews = relationship("Review", back_populates="author")
