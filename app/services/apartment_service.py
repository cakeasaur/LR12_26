from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.apartment import Apartment
from app.schemas.apartment import ApartmentCreate, ApartmentUpdate


def create_apartment(db: Session, data: ApartmentCreate, owner_id: int) -> Apartment:
    apartment = Apartment(**data.model_dump(), owner_id=owner_id)
    db.add(apartment)
    db.commit()
    db.refresh(apartment)
    return apartment


def get_apartment(db: Session, apartment_id: int) -> Optional[Apartment]:
    return db.query(Apartment).filter(Apartment.id == apartment_id).first()


def get_apartments(
    db: Session,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Apartment]:
    query = db.query(Apartment).filter(Apartment.is_active == True)
    if city:
        query = query.filter(Apartment.city.ilike(f"%{city}%"))
    if min_price is not None:
        query = query.filter(Apartment.price_per_night >= min_price)
    if max_price is not None:
        query = query.filter(Apartment.price_per_night <= max_price)
    return query.offset(skip).limit(limit).all()


def update_apartment(
    db: Session, apartment: Apartment, data: ApartmentUpdate
) -> Apartment:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(apartment, field, value)
    db.commit()
    db.refresh(apartment)
    return apartment


def delete_apartment(db: Session, apartment: Apartment) -> None:
    apartment.is_active = False
    db.commit()
