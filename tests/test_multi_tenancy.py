import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Header

from app.main import app
from app.api import deps
from app.models.auth import School, User

client = TestClient(app)


@pytest.mark.asyncio
async def test_api_key_header_verification() -> None:
    """Verifies that verify_api_key rejects unauthorized calls and handles active schools correctly."""
    mock_db = AsyncMock()
    
    # Arrange 1: Invalid API Key
    mock_db.scalar = AsyncMock(return_value=None)
    with pytest.raises(Exception) as exc_info:
        await deps.verify_api_key(x_api_key="mg_invalid_key", db=mock_db)
    assert "Invalid or revoked API Key" in str(exc_info.value)
    
    # Arrange 2: Valid API Key
    mock_school = School(id=1, name="Stanford University", api_key="mg_stanford_valid")
    mock_db.scalar = AsyncMock(return_value=mock_school)
    
    school = await deps.verify_api_key(x_api_key="mg_stanford_valid", db=mock_db)
    assert school is not None
    assert school.id == 1
    assert school.name == "Stanford University"


@pytest.mark.asyncio
async def test_student_data_resolver_isolation() -> None:
    """Asserts that resolve_student_id enforces correct boundaries for JWT users and API Keys."""
    mock_db = AsyncMock()
    
    # 1. Calls with X-API-Key return "api_authorized" to delegate target checking
    mock_school = School(id=2, name="Berkeley University", api_key="mg_berkeley")
    mock_db.scalar = AsyncMock(return_value=mock_school)
    
    res = await deps.resolve_student_id(x_api_key="mg_berkeley", token=None, db=mock_db)
    assert res == "api_authorized"
    
    # 2. Calls with valid JWT resolve the student_id from current_user
    mock_user = User(id="student_berkeley", email="student@berkeley.edu", hashed_password="hashed_pass")
    
    with patch("app.services.auth_service.AuthService.decode_access_token", return_value={"sub": "student@berkeley.edu"}):
        mock_db.scalar = AsyncMock(return_value=mock_user)
        student_id = await deps.resolve_student_id(x_api_key=None, token="valid_jwt_token", db=mock_db)
        assert student_id == "student_berkeley"
