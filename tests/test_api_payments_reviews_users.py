"""Тесты API: payments, reviews, users."""
from datetime import date, timedelta

import pytest

from app.models.booking import BookingStatus
from app.services.booking_service import update_booking_status
from app.services.payment_service import create_payment
from app.schemas.payment import PaymentCreate


# ════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════════════════

class TestPayments:
    def test_pay_booking_success(self, client, tenant_token, booking):
        r = client.post("/api/v1/payments/", json={
            "booking_id": booking.id,
            "transaction_ref": "TXN-001",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 201
        data = r.json()
        assert data["booking_id"] == booking.id
        assert data["status"] == "held"

    def test_pay_booking_not_found(self, client, tenant_token):
        r = client.post("/api/v1/payments/", json={
            "booking_id": 9999,
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_pay_booking_not_owner(self, client, landlord_token, booking):
        r = client.post("/api/v1/payments/", json={
            "booking_id": booking.id,
        }, headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 403

    def test_pay_booking_already_paid(self, client, db, tenant_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        r = client.post("/api/v1/payments/", json={
            "booking_id": booking.id,
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 409

    def test_get_payment_as_tenant(self, client, db, tenant_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        r = client.get(f"/api/v1/payments/{booking.id}",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["booking_id"] == booking.id

    def test_get_payment_as_landlord(self, client, db, landlord_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        r = client.get(f"/api/v1/payments/{booking.id}",
                       headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200

    def test_get_payment_booking_not_found(self, client, tenant_token):
        r = client.get("/api/v1/payments/9999",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_get_payment_not_found(self, client, tenant_token, booking):
        r = client.get(f"/api/v1/payments/{booking.id}",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_release_payment_as_landlord(self, client, db, landlord_token, booking):
        update_booking_status(db, booking, BookingStatus.confirmed)
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        update_booking_status(db, booking, BookingStatus.completed)
        r = client.post(f"/api/v1/payments/{booking.id}/release",
                        headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200
        assert r.json()["status"] == "released"

    def test_release_payment_booking_not_found(self, client, landlord_token):
        r = client.post("/api/v1/payments/9999/release",
                        headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 404

    def test_release_payment_not_found(self, client, db, landlord_token, booking):
        update_booking_status(db, booking, BookingStatus.completed)
        r = client.post(f"/api/v1/payments/{booking.id}/release",
                        headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 404

    def test_release_payment_forbidden(self, client, db, tenant_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        update_booking_status(db, booking, BookingStatus.completed)
        r = client.post(f"/api/v1/payments/{booking.id}/release",
                        headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_refund_payment_success(self, client, db, tenant_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        update_booking_status(db, booking, BookingStatus.cancelled)
        r = client.post(f"/api/v1/payments/{booking.id}/refund",
                        headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["status"] == "refunded"

    def test_refund_not_cancelled(self, client, db, tenant_token, booking):
        create_payment(db, PaymentCreate(booking_id=booking.id), amount=booking.total_price)
        r = client.post(f"/api/v1/payments/{booking.id}/refund",
                        headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 400

    def test_refund_booking_not_found(self, client, tenant_token):
        r = client.post("/api/v1/payments/9999/refund",
                        headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_refund_payment_not_found(self, client, db, tenant_token, booking):
        update_booking_status(db, booking, BookingStatus.cancelled)
        r = client.post(f"/api/v1/payments/{booking.id}/refund",
                        headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════════════
# REVIEWS
# ════════════════════════════════════════════════════════════════════════════

class TestReviews:
    def test_list_reviews_empty(self, client, apartment):
        r = client.get(f"/api/v1/reviews/apartments/{apartment.id}")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_review_success(self, client, db, tenant_token, completed_booking, apartment):
        r = client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id,
            "rating": 5,
            "comment": "Отличное место!",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 201
        assert r.json()["rating"] == 5

    def test_create_review_no_completed_booking(self, client, tenant_token, apartment):
        r = client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id,
            "rating": 4,
            "comment": "Хорошо",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_list_reviews_after_create(self, client, db, tenant_token, completed_booking, apartment):
        client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id, "rating": 4, "comment": "Ok",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        r = client.get(f"/api/v1/reviews/apartments/{apartment.id}")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_delete_review_as_author(self, client, db, tenant_token, completed_booking, apartment):
        create_r = client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id, "rating": 3, "comment": "Норм",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        review_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/reviews/{review_id}",
                          headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 204

    def test_delete_review_as_admin(self, client, db, tenant_token, admin_token, completed_booking, apartment):
        create_r = client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id, "rating": 2, "comment": "Плохо",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        review_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/reviews/{review_id}",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 204

    def test_delete_review_not_found(self, client, tenant_token):
        r = client.delete("/api/v1/reviews/9999",
                          headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_delete_review_forbidden(self, client, db, tenant_token, landlord_token, completed_booking, apartment):
        create_r = client.post("/api/v1/reviews/", json={
            "apartment_id": apartment.id, "rating": 5, "comment": "Супер",
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        review_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/reviews/{review_id}",
                          headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════════════════════

class TestUsers:
    def test_get_me(self, client, tenant_token, tenant):
        r = client.get("/api/v1/users/me",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["email"] == tenant.email

    def test_update_me(self, client, tenant_token):
        r = client.put("/api/v1/users/me",
                       json={"full_name": "Обновлённое имя"},
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["full_name"] == "Обновлённое имя"

    def test_list_users_as_admin(self, client, admin_token, tenant, landlord):
        r = client.get("/api/v1/users/",
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_list_users_forbidden_for_tenant(self, client, tenant_token):
        r = client.get("/api/v1/users/",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_deactivate_user_as_admin(self, client, db, admin_token, tenant):
        r = client.delete(f"/api/v1/users/{tenant.id}",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 204
        db.refresh(tenant)
        assert tenant.is_active is False

    def test_deactivate_user_not_found(self, client, admin_token):
        r = client.delete("/api/v1/users/9999",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 404

    def test_deactivate_user_forbidden(self, client, tenant_token, landlord):
        r = client.delete(f"/api/v1/users/{landlord.id}",
                          headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403
