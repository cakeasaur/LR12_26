from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token
from app.db.base import get_db
from app.models.booking import BookingStatus
from app.models.user import UserRole
from app.schemas.apartment import ApartmentCreate, ApartmentUpdate
from app.schemas.booking import BookingCreate
from app.schemas.user import UserCreate
from app.services import (
    apartment_service, booking_service, payment_service, review_service, user_service,
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

COOKIE_NAME = "access_token"


def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    return user_service.get_user_by_id(db, user_id=int(payload.get("sub")))


# ---------- Главная ----------

@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    apartments = apartment_service.get_apartments(
        db, city=city, min_price=min_price, max_price=max_price, limit=50
    )
    return templates.TemplateResponse(request, "index.html", {
        "apartments": apartments,
        "user": user,
        "filters": {"city": city, "min_price": min_price, "max_price": max_price},
    })


# ---------- Аутентификация ----------

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_current_user_from_cookie)):
    if user:
        return RedirectResponse("/profile", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"user": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = user_service.authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {
            "user": None,
            "error": "Неверный email или пароль",
        })
    token = create_access_token(data={"sub": str(user.id)})
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, max_age=3600 * 24)
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user=Depends(get_current_user_from_cookie)):
    if user:
        return RedirectResponse("/profile", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"user": None})


@router.post("/register")
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: Optional[str] = Form(None),
    role: str = Form("tenant"),
    db: Session = Depends(get_db),
):
    if user_service.get_user_by_email(db, email):
        return templates.TemplateResponse(request, "register.html", {
            "user": None,
            "error": "Email уже зарегистрирован",
        })
    try:
        data = UserCreate(
            email=email, password=password, full_name=full_name,
            phone=phone or None, role=UserRole(role),
        )
        user = user_service.create_user(db, data)
    except Exception as e:
        return templates.TemplateResponse(request, "register.html", {
            "user": None, "error": str(e),
        })
    token = create_access_token(data={"sub": str(user.id)})
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, max_age=3600 * 24)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---------- Квартиры ----------

@router.get("/apartments/new", response_class=HTMLResponse)
def new_apartment_page(request: Request, user=Depends(get_current_user_from_cookie)):
    if not user or user.role not in (UserRole.landlord, UserRole.admin):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "apartment_form.html", {"user": user, "apt": None})


@router.post("/apartments/new")
def new_apartment_submit(
    request: Request,
    title: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    description: Optional[str] = Form(None),
    price_per_night: float = Form(...),
    rooms: int = Form(...),
    max_guests: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user or user.role not in (UserRole.landlord, UserRole.admin):
        return RedirectResponse("/login", status_code=302)
    try:
        data = ApartmentCreate(
            title=title, address=address, city=city, description=description,
            price_per_night=price_per_night, rooms=rooms, max_guests=max_guests,
        )
        apt = apartment_service.create_apartment(db, data, owner_id=user.id)
    except Exception as e:
        return templates.TemplateResponse(request, "apartment_form.html", {
            "user": user, "apt": None, "error": str(e),
        })
    return RedirectResponse(f"/apartments/{apt.id}", status_code=302)


@router.get("/apartments/{apartment_id}", response_class=HTMLResponse)
def apartment_detail(
    request: Request,
    apartment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    apt = apartment_service.get_apartment(db, apartment_id)
    if not apt:
        return RedirectResponse("/", status_code=302)
    reviews = review_service.get_apartment_reviews(db, apartment_id)
    is_owner = user and user.id == apt.owner_id
    can_review = (
        user and not is_owner
        and review_service.has_completed_booking(db, user.id, apartment_id)
        and not any(r.author_id == user.id for r in reviews)
    )
    return templates.TemplateResponse(request, "apartment.html", {
        "apt": apt, "user": user,
        "reviews": reviews, "is_owner": is_owner,
        "can_review": can_review,
    })


@router.get("/apartments/{apartment_id}/edit", response_class=HTMLResponse)
def edit_apartment_page(
    request: Request,
    apartment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    apt = apartment_service.get_apartment(db, apartment_id)
    if not apt or not user or (user.id != apt.owner_id and user.role != UserRole.admin):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "apartment_form.html", {"user": user, "apt": apt})


@router.post("/apartments/{apartment_id}/edit")
def edit_apartment_submit(
    request: Request,
    apartment_id: int,
    title: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    description: Optional[str] = Form(None),
    price_per_night: float = Form(...),
    rooms: int = Form(...),
    max_guests: int = Form(...),
    is_active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    apt = apartment_service.get_apartment(db, apartment_id)
    if not apt or not user or (user.id != apt.owner_id and user.role != UserRole.admin):
        return RedirectResponse("/", status_code=302)
    data = ApartmentUpdate(
        title=title, address=address, city=city, description=description,
        price_per_night=price_per_night, rooms=rooms, max_guests=max_guests,
        is_active=is_active == "on",
    )
    apartment_service.update_apartment(db, apt, data)
    return RedirectResponse(f"/apartments/{apartment_id}", status_code=302)


# ---------- Оплата ----------

@router.post("/payments/pay/{booking_id}")
def pay_booking_web(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking and booking.tenant_id == user.id:
        if not payment_service.get_payment_by_booking(db, booking_id):
            from app.schemas.payment import PaymentCreate
            payment_service.create_payment(
                db, PaymentCreate(booking_id=booking_id), amount=booking.total_price
            )
            booking_service.update_booking_status(db, booking, BookingStatus.confirmed)
    return RedirectResponse("/profile", status_code=302)


@router.post("/payments/refund/{booking_id}")
def refund_booking_web(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking and booking.tenant_id == user.id:
        payment = payment_service.get_payment_by_booking(db, booking_id)
        if payment:
            payment_service.refund_payment(db, payment)
    return RedirectResponse("/profile", status_code=302)


# ---------- Отзывы ----------

@router.post("/reviews")
def create_review_web(
    apartment_id: int = Form(...),
    rating: int = Form(...),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    from app.schemas.review import ReviewCreate
    try:
        data = ReviewCreate(apartment_id=apartment_id, rating=rating, comment=comment)
        review_service.create_review(db, data, author_id=user.id)
    except Exception:
        pass
    return RedirectResponse(f"/apartments/{apartment_id}", status_code=302)


# ---------- Бронирования ----------

@router.post("/bookings")
def create_booking(
    request: Request,
    apartment_id: int = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    from datetime import date
    try:
        data = BookingCreate(
            apartment_id=apartment_id,
            check_in=date.fromisoformat(check_in),
            check_out=date.fromisoformat(check_out),
        )
        if not booking_service.check_availability(db, apartment_id, data.check_in, data.check_out):
            apt = apartment_service.get_apartment(db, apartment_id)
            reviews = review_service.get_apartment_reviews(db, apartment_id)
            return templates.TemplateResponse(request, "apartment.html", {
                "apt": apt, "user": user,
                "reviews": reviews, "is_owner": False,
                "flash": {"type": "danger", "message": "Квартира недоступна на выбранные даты"},
            })
        booking_service.create_booking(db, data, tenant_id=user.id)
    except Exception as e:
        apt = apartment_service.get_apartment(db, apartment_id)
        reviews = review_service.get_apartment_reviews(db, apartment_id)
        return templates.TemplateResponse(request, "apartment.html", {
            "apt": apt, "user": user,
            "reviews": reviews, "is_owner": False,
            "flash": {"type": "danger", "message": str(e)},
        })
    return RedirectResponse("/profile", status_code=302)


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking and booking.tenant_id == user.id:
        booking_service.update_booking_status(db, booking, BookingStatus.cancelled)
    return RedirectResponse("/profile", status_code=302)


@router.post("/bookings/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking:
        apt = apartment_service.get_apartment(db, booking.apartment_id)
        if apt and apt.owner_id == user.id:
            booking_service.update_booking_status(db, booking, BookingStatus.confirmed)
    return RedirectResponse("/profile", status_code=302)


@router.post("/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking:
        apt = apartment_service.get_apartment(db, booking.apartment_id)
        if apt and apt.owner_id == user.id:
            booking_service.update_booking_status(db, booking, BookingStatus.completed)
    return RedirectResponse("/profile", status_code=302)


@router.post("/bookings/{booking_id}/cancel-landlord")
def cancel_booking_landlord(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = booking_service.get_booking(db, booking_id)
    if booking:
        apt = apartment_service.get_apartment(db, booking.apartment_id)
        if apt and apt.owner_id == user.id:
            booking_service.update_booking_status(db, booking, BookingStatus.cancelled)
    return RedirectResponse("/profile", status_code=302)


# ---------- Профиль ----------

@router.get("/profile", response_class=HTMLResponse)
def profile(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    bookings = booking_service.get_user_bookings(db, tenant_id=user.id)
    apartments = []
    incoming_bookings = []
    if user.role in (UserRole.landlord, UserRole.admin):
        from app.models.apartment import Apartment
        from app.models.booking import Booking
        apartments = db.query(Apartment).filter(Apartment.owner_id == user.id).all()
        apt_ids = [a.id for a in apartments]
        apt_titles = {a.id: a.title for a in apartments}
        if apt_ids:
            raw = db.query(Booking).filter(Booking.apartment_id.in_(apt_ids)).all()
            for b in raw:
                b.apt_title = apt_titles.get(b.apartment_id, f"№{b.apartment_id}")
            incoming_bookings = raw
    paid_booking_ids = {
        b.id for b in bookings
        if payment_service.get_payment_by_booking(db, b.id)
    }
    return templates.TemplateResponse(request, "profile.html", {
        "user": user,
        "bookings": bookings,
        "apartments": apartments,
        "incoming_bookings": incoming_bookings,
        "paid_booking_ids": paid_booking_ids,
    })


# ---------- Админ-панель ----------

@router.get("/admin", response_class=HTMLResponse)
def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user or user.role != UserRole.admin:
        return RedirectResponse("/", status_code=302)
    from app.models.user import User as UserModel
    from app.models.apartment import Apartment
    from app.models.booking import Booking
    from app.models.payment import Payment
    users = db.query(UserModel).all()
    stats = {
        "users": db.query(UserModel).count(),
        "apartments": db.query(Apartment).count(),
        "bookings": db.query(Booking).count(),
        "payments": db.query(Payment).count(),
    }
    return templates.TemplateResponse(request, "admin.html", {
        "user": user, "current_user": user,
        "users": users, "stats": stats,
    })


@router.post("/admin/users/{user_id}/deactivate")
def deactivate_user_web(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user or user.role != UserRole.admin:
        return RedirectResponse("/", status_code=302)
    from app.models.user import User as UserModel
    target = db.query(UserModel).filter(UserModel.id == user_id).first()
    if target and target.id != user.id:
        target.is_active = False
        db.commit()
    return RedirectResponse("/admin", status_code=302)


@router.post("/admin/users/{user_id}/activate")
def activate_user_web(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_from_cookie),
):
    if not user or user.role != UserRole.admin:
        return RedirectResponse("/", status_code=302)
    from app.models.user import User as UserModel
    target = db.query(UserModel).filter(UserModel.id == user_id).first()
    if target:
        target.is_active = True
        db.commit()
    return RedirectResponse("/admin", status_code=302)
