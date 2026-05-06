"""Тесты API: квартиры."""
import pytest


class TestListApartments:
    def test_list_empty(self, client):
        r = client.get("/api/v1/apartments/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_with_apartments(self, client, apartment):
        r = client.get("/api/v1/apartments/")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filter_by_city(self, client, apartment):
        r = client.get("/api/v1/apartments/?city=Москва")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filter_by_city_no_match(self, client, apartment):
        r = client.get("/api/v1/apartments/?city=Питер")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_filter_min_price(self, client, apartment):
        r = client.get("/api/v1/apartments/?min_price=5000")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_filter_max_price(self, client, apartment):
        r = client.get("/api/v1/apartments/?max_price=1000")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_pagination(self, client, apartment):
        r = client.get("/api/v1/apartments/?skip=0&limit=10")
        assert r.status_code == 200


class TestGetApartment:
    def test_get_existing(self, client, apartment):
        r = client.get(f"/api/v1/apartments/{apartment.id}")
        assert r.status_code == 200
        assert r.json()["id"] == apartment.id

    def test_get_not_found(self, client):
        r = client.get("/api/v1/apartments/9999")
        assert r.status_code == 404

    def test_get_inactive(self, client, db, apartment):
        apartment.is_active = False
        db.commit()
        r = client.get(f"/api/v1/apartments/{apartment.id}")
        assert r.status_code == 404


class TestCreateApartment:
    def _payload(self):
        return {
            "title": "Новая квартира",
            "address": "ул. Тестовая, 1",
            "city": "Казань",
            "price_per_night": 1500.0,
            "rooms": 2,
            "max_guests": 3,
        }

    def test_create_as_landlord(self, client, landlord_token):
        r = client.post("/api/v1/apartments/", json=self._payload(), headers={
            "Authorization": f"Bearer {landlord_token}"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Новая квартира"
        assert data["city"] == "Казань"

    def test_create_as_tenant_forbidden(self, client, tenant_token):
        r = client.post("/api/v1/apartments/", json=self._payload(), headers={
            "Authorization": f"Bearer {tenant_token}"
        })
        assert r.status_code == 403

    def test_create_no_auth(self, client):
        r = client.post("/api/v1/apartments/", json=self._payload())
        assert r.status_code == 401

    def test_create_invalid_price(self, client, landlord_token):
        payload = self._payload()
        payload["price_per_night"] = -100
        r = client.post("/api/v1/apartments/", json=payload, headers={
            "Authorization": f"Bearer {landlord_token}"
        })
        assert r.status_code == 422

    def test_create_as_admin(self, client, admin_token):
        r = client.post("/api/v1/apartments/", json=self._payload(), headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 201


class TestUpdateApartment:
    def test_update_as_owner(self, client, apartment, landlord_token):
        r = client.put(f"/api/v1/apartments/{apartment.id}",
                       json={"title": "Обновлённое название"},
                       headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 200
        assert r.json()["title"] == "Обновлённое название"

    def test_update_not_owner_forbidden(self, client, apartment, tenant_token):
        r = client.put(f"/api/v1/apartments/{apartment.id}",
                       json={"title": "Чужое"},
                       headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_update_not_found(self, client, landlord_token):
        r = client.put("/api/v1/apartments/9999",
                       json={"title": "X"},
                       headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 404

    def test_update_as_admin(self, client, apartment, admin_token):
        r = client.put(f"/api/v1/apartments/{apartment.id}",
                       json={"city": "Новосибирск"},
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["city"] == "Новосибирск"


class TestDeleteApartment:
    def test_delete_as_owner(self, client, apartment, landlord_token):
        r = client.delete(f"/api/v1/apartments/{apartment.id}",
                          headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 204

    def test_delete_not_owner_forbidden(self, client, apartment, tenant_token):
        r = client.delete(f"/api/v1/apartments/{apartment.id}",
                          headers={"Authorization": f"Bearer {tenant_token}"})
        assert r.status_code == 403

    def test_delete_not_found(self, client, landlord_token):
        r = client.delete("/api/v1/apartments/9999",
                          headers={"Authorization": f"Bearer {landlord_token}"})
        assert r.status_code == 404
