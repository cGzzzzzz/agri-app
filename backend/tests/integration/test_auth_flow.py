class TestAuthFlow:
    def test_register_user(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "name": "New User",
                "password": "SecurePass123!",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_register_duplicate_email(self, client, db_user):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "name": "Dup",
                "password": "Pass123!",
            },
        )
        assert resp.status_code == 409

    def test_login_success(self, client, db_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data["tokens"]

    def test_login_wrong_password(self, client, db_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPass",
            },
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "noone@example.com",
                "password": "Pass",
            },
        )
        assert resp.status_code == 401

    def test_me_with_valid_token(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "test@example.com"

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_refresh_token(self, client, db_user):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        refresh = login_resp.json()["data"]["tokens"]["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401
