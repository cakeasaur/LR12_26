from typing import Optional
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking
from app.schemas.payment import PaymentCreate


def create_payment(db: Session, data: PaymentCreate, amount: float) -> Payment:
    payment = Payment(
        booking_id=data.booking_id,
        amount=amount,
        status=PaymentStatus.held,
        transaction_ref=data.transaction_ref,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment_by_booking(db: Session, booking_id: int) -> Optional[Payment]:
    return db.query(Payment).filter(Payment.booking_id == booking_id).first()


def release_payment(db: Session, payment: Payment) -> Payment:
    """Перевести деньги арендодателю после завершения аренды."""
    payment.status = PaymentStatus.released
    db.commit()
    db.refresh(payment)
    return payment


def refund_payment(db: Session, payment: Payment) -> Payment:
    """Вернуть деньги арендатору при отмене."""
    payment.status = PaymentStatus.refunded
    db.commit()
    db.refresh(payment)
    return payment
