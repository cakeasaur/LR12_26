from typing import Optional
from pydantic import BaseModel, field_validator


class ApartmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    address: str
    city: str
    price_per_night: float
    rooms: int
    max_guests: int

    @field_validator("price_per_night")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Цена должна быть больше нуля")
        return v

    @field_validator("rooms", "max_guests")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Значение должно быть больше нуля")
        return v


class ApartmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    price_per_night: Optional[float] = None
    rooms: Optional[int] = None
    max_guests: Optional[int] = None
    is_active: Optional[bool] = None


class ApartmentRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    address: str
    city: str
    price_per_night: float
    rooms: int
    max_guests: int
    is_active: bool
    owner_id: int

    model_config = {"from_attributes": True}
