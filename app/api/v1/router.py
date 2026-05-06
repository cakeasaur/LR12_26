from fastapi import APIRouter

from app.api.v1.endpoints import auth, apartments, bookings, payments, reviews, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(apartments.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(reviews.router)
