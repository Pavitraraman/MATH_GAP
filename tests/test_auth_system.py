import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

from app.main import app
from app.services.auth_service import AuthService
from app.models.auth import User, School

client = TestClient(app)


def test_password_hashing_and_verification() -> None:
    """Verifies that PBKDF2-SHA256 password salting and verification operates securely and correctly."""
    plain_password = "pavitra_secure_password"
    
    # Act: Hash password
    hashed = AuthService.hash_password(plain_password)
    
    # Assert format
    assert hashed.startswith("pbkdf2_sha256$100000$")
    
    # Verify correctness
    assert AuthService.verify_password(plain_password, hashed) is True
    
    # Verify failure on incorrect password
    assert AuthService.verify_password("wrong_password", hashed) is False
    assert AuthService.verify_password("", hashed) is False


def test_jwt_access_tokens() -> None:
    """Verifies that JWT access token encoding and decoding works with signatures."""
    payload = {"sub": "student@stanford.edu", "role": "student"}
    
    # Act: Encode
    token = AuthService.create_access_token(payload)
    assert isinstance(token, str)
    
    # Act: Decode
    decoded = AuthService.decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "student@stanford.edu"
    assert decoded["role"] == "student"
    
    # Assert failure on corrupted token
    corrupted_token = token + "corrupted"
    assert AuthService.decode_access_token(corrupted_token) is None


@patch("app.api.routes.auth.AuthService")
@pytest.mark.asyncio
async def test_auth_routes_signup_and_login(mock_auth_class) -> None:
    """Mocks database lookups to verify user registration and authorization routes."""
    # Mock Select to pretend email/username do not exist (allows signup)
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Formulate payload
    signup_data = {
        "username": "student_test",
        "email": "student@school.edu",
        "password": "secure_password",
        "role": "student",
        "school_name": "Test Academy"
    }
    
    # Mock select statement results
    mock_auth_class.hash_password.return_value = "pbkdf2_sha256$100000$mockedsalt$mockedhash"
    mock_auth_class.create_access_token.return_value = "mocked_jwt_access_token"
    
    # Trigger signup endpoint
    from app.api import deps
    app.dependency_overrides[deps.get_db] = lambda: mock_db
    
    try:
        response = client.post("/auth/signup", json=signup_data)
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mocked_jwt_access_token"
        assert data["role"] == "student"
        assert data["username"] == "student_test"
    finally:
        app.dependency_overrides.clear()
