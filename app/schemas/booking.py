from datetime import date
from pydantic import BaseModel, model_validator
from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    apartment_id: int
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def check_dates(self) -> "BookingCreate":
        if self.check_out <= self.check_in:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        if self.check_in < date.today():
            raise ValueError("Дата заезда не может быть в прошлом")
        return self


class BookingRead(BaseModel):
    id: int
    apartment_id: int
    tenant_id: int
    check_in: date
    check_out: date
    total_price: float
    status: BookingStatus

    model_config = {"from_attributes": True}


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
