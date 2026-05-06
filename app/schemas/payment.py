from typing import Optional
from pydantic import BaseModel
from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: int
    transaction_ref: Optional[str] = None


class PaymentRead(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: PaymentStatus
    transaction_ref: Optional[str]

    model_config = {"from_attributes": True}
