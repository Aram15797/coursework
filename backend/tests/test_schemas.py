import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


def test_user_create_valid():
    user = UserCreate(
        email="test@example.com",
        username="tester",
        password="secret123",
        full_name="Test User",
    )
    assert user.email == "test@example.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", username="x", password="123456")


def test_user_create_short_password():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", username="abc", password="123")
