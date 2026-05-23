import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.auth import User, School
from app.services.auth_service import AuthService

logger = logging.getLogger("math_gap.auth_router")

router = APIRouter()


# --- AUTHENTICATION SCHEMAS ---

class UserSignupRequest(BaseModel):
    username: str  # user id / login handle
    email: EmailStr
    password: str
    role: str = "student"  # "student", "teacher", "admin"
    school_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    school_id: Optional[int] = None
    school_api_key: Optional[str] = None


# --- ENDPOINTS ---

@router.post("/signup", response_model=TokenResponse)
async def signup(
    request: UserSignupRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> TokenResponse:
    """Signs up a new user, hashes their password, and creates their sandbox/production school tenant if requested."""
    try:
        # Check password strength
        if len(request.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long",
            )

        # Assert unique email
        email_stmt = select(User).where(User.email == request.email)
        existing_email = await db.scalar(email_stmt)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered",
            )

        # Assert unique username / id
        id_stmt = select(User).where(User.id == request.username)
        existing_username = await db.scalar(id_stmt)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Link or create school
        school_id = None
        school_api_key = None
        if request.school_name:
            # Clean and capitalize
            s_name = request.school_name.strip()
            school_stmt = select(School).where(School.name == s_name)
            school = await db.scalar(school_stmt)
            if not school:
                # Create school on the fly (useful for sandbox tests and coaches)
                school = School(name=s_name)
                db.add(school)
                await db.commit()
                await db.refresh(school)
                logger.info("Automatically created new school tenant: %s", s_name)
            
            school_id = school.id
            school_api_key = school.api_key

        # Create user
        hashed = AuthService.hash_password(request.password)
        new_user = User(
            id=request.username.strip(),
            email=request.email,
            hashed_password=hashed,
            role=request.role.lower(),
            school_id=school_id,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Automatically yield JWT access token on success
        access_token = AuthService.create_access_token({"sub": new_user.email})

        return TokenResponse(
            access_token=access_token,
            role=new_user.role,
            username=new_user.id,
            school_id=school_id,
            school_api_key=school_api_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to sign up user.")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> TokenResponse:
    """Authenticates credentials and returns a secure JWT access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Find user
        stmt = select(User).where(User.email == request.email)
        user = await db.scalar(stmt)
        if not user:
            raise credentials_exception

        # Verify password
        if not AuthService.verify_password(request.password, user.hashed_password):
            raise credentials_exception

        # Fetch school API key if user belongs to one
        school_api_key = None
        if user.school_id:
            school_stmt = select(School).where(School.id == user.school_id)
            school = await db.scalar(school_stmt)
            if school:
                school_api_key = school.api_key

        # Generate token
        access_token = AuthService.create_access_token({"sub": user.email})

        return TokenResponse(
            access_token=access_token,
            role=user.role,
            username=user.id,
            school_id=user.school_id,
            school_api_key=school_api_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to login user.")
        raise HTTPException(status_code=500, detail=str(exc))
