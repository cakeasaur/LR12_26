"""Тесты API: аутентификация и пользователи."""
import pytest


class TestRegister:
    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "password123",
            "full_name": "New User",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@test.com"
        assert data["role"] == "tenant"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_email(self, client, tenant):
        r = client.post("/api/v1/auth/register", json={
            "email": "tenant@test.com",
            "password": "password123",
            "full_name": "Another",
        })
        assert r.status_code == 400
        assert "Email" in r.json()["detail"]

    def test_register_short_password(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "short",
            "full_name": "User",
        })
        assert r.status_code == 422

    def test_register_invalid_email(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "full_name": "User",
        })
        assert r.status_code == 422

    def test_register_role_cannot_be_set_by_client(self, client):
        """Переданная роль игнорируется — пользователь всегда создаётся как tenant."""
        r = client.post("/api/v1/auth/register", json={
            "email": "attacker@test.com",
            "password": "password123",
            "full_name": "Attacker",
            "role": "admin",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "tenant"


class TestLogin:
    def test_login_success(self, client, tenant):
        r = client.post("/api/v1/auth/login", data={
            "username": "tenant@test.com",
            "password": "password123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, tenant):
        r = client.post("/api/v1/auth/login", data={
            "username": "tenant@test.com",
            "password": "wrongpassword",
        })
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = client.post("/api/v1/auth/login", data={
            "username": "nobody@test.com",
            "password": "password123",
        })
        assert r.status_code == 401

    def test_login_inactive_user(self, client, db, tenant):
        tenant.is_active = False
        db.commit()
        r = client.post("/api/v1/auth/login", data={
            "username": "tenant@test.com",
            "password": "password123",
        })
        assert r.status_code == 401


class TestProtectedEndpoints:
    def test_no_token_returns_401(self, client):
        r = client.get("/api/v1/bookings/my")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        r = client.get("/api/v1/bookings/my", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert r.status_code == 401
