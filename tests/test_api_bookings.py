"""Тесты API: бронирования."""
from datetime import date, timedelta

import pytest

from app.models.booking import BookingStatus


def future_dates(start=1, end=3):
    return (
        (date.today() + timedelta(days=start)).isoformat(),
        (date.today() + timedelta(days=end)).isoformat(),
    )


class TestCreateBooking:
    def test_create_success(self, client, tenant_token, apartment):
        check_in, check_out = future_dates(2, 5)
        r = client.post("/api/v1/bookings/", json={
            "apartment_id": apartment.id,
            "check_in": check_in,
            "check_out": check_out,
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 201
        data = r.json()
        assert data["apartment_id"] == apartment.id
        assert data["status"] == "pending"

    def test_create_no_auth(self, client, apartment):
        check_in, check_out = future_dates()
        r = client.post("/api/v1/bookings/", json={
            "apartment_id": apartment.id,
            "check_in": check_in,
            "check_out": check_out,
        })
        assert r.status_code == 401

    def test_create_apartment_not_found(self, client, tenant_token):
        check_in, check_out = future_dates()
        r = client.post("/api/v1/bookings/", json={
            "apartment_id": 9999,
            "check_in": check_in,
            "check_out": check_out,
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_create_conflict(self, client, tenant_token, apartment, booking):
        # booking занимает days +1 .. +3, пробуем +2 .. +4
        check_in = (date.today() + timedelta(days=2)).isoformat()
        check_out = (date.today() + timedelta(days=4)).isoformat()
        r = client.post("/api/v1/bookings/", json={
            "apartment_id": apartment.id,
            "check_in": check_in,
            "check_out": check_out,
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 409

    def test_create_check_out_before_check_in(self, client, tenant_token, apartment):
        r = client.post("/api/v1/bookings/", json={
            "apartment_id": apartment.id,
            "check_in": (date.today() + timedelta(days=5)).isoformat(),
            "check_out": (date.today() + timedelta(days=2)).isoformat(),
        }, headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 422


class TestGetBooking:
    def test_get_own_booking(self, client, tenant_token, booking):
        r = client.get(f"/api/v1/bookings/{booking.id}",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["id"] == booking.id

    def test_get_as_landlord_owner(self, client, landlord_token, booking):
        r = client.get(f"/api/v1/bookings/{booking.id}",
                       headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200

    def test_get_not_found(self, client, tenant_token):
        r = client.get("/api/v1/bookings/9999",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_get_my_bookings(self, client, tenant_token, booking):
        r = client.get("/api/v1/bookings/my",
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestUpdateBookingStatus:
    def test_tenant_can_cancel(self, client, tenant_token, booking):
        r = client.patch(f"/api/v1/bookings/{booking.id}/status",
                         json={"status": "cancelled"},
                         headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_tenant_cannot_confirm(self, client, tenant_token, booking):
        r = client.patch(f"/api/v1/bookings/{booking.id}/status",
                         json={"status": "confirmed"},
                         headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_landlord_can_confirm(self, client, landlord_token, booking):
        r = client.patch(f"/api/v1/bookings/{booking.id}/status",
                         json={"status": "confirmed"},
                         headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_landlord_can_complete(self, client, landlord_token, booking):
        r = client.patch(f"/api/v1/bookings/{booking.id}/status",
                         json={"status": "completed"},
                         headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_update_not_found(self, client, tenant_token):
        r = client.patch("/api/v1/bookings/9999/status",
                         json={"status": "cancelled"},
                         headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 404

    def test_admin_can_update(self, client, admin_token, booking):
        r = client.patch(f"/api/v1/bookings/{booking.id}/status",
                         json={"status": "confirmed"},
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
