from datetime import timedelta

from app.services.security import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pwd = "MySecureP@ss123"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert verify_password(pwd, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_input(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed)


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token(42)
        user_id = decode_token(token, "access")
        assert user_id == 42

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token(99)
        user_id = decode_token(token, "refresh")
        assert user_id == 99

    def test_wrong_token_type_returns_none(self):
        token = create_access_token(1)
        assert decode_token(token, "refresh") is None

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.valid.token") is None

    def test_empty_token_returns_none(self):
        assert decode_token("") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token(1)
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_custom_token_expiry(self):
        token = create_token("7", "access", timedelta(seconds=-1))
        assert decode_token(token, "access") is None
