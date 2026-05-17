from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-id", {"role": "member"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"
    assert payload["role"] == "member"


def test_refresh_token_type():
    token = create_refresh_token("user-id")
    payload = decode_token(token)
    assert payload is not None
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    assert decode_token("not-a-token") is None
