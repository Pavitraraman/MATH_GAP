from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.auth import User, School
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that authenticates standard user JWT tokens and yields the user entity."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = AuthService.decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    stmt = select(User).where(User.email == email)
    user = await db.scalar(stmt)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Yields current authenticated and active user."""
    return current_user


async def get_current_teacher_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Restricts route access to users with teacher or admin clearance roles."""
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> School:
    """Validates programmatic institutional client requests using X-API-Key header values."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing from headers",
        )
    stmt = select(School).where(School.api_key == x_api_key)
    school = await db.scalar(stmt)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key",
        )
    return school


async def resolve_student_id(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Resolves student_id either from verified JWT session token or signals programmatic API-Key authorization."""
    if x_api_key:
        stmt = select(School).where(School.api_key == x_api_key)
        school = await db.scalar(stmt)
        if not school:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API Key",
            )
        return "api_authorized"

    if token:
        payload = AuthService.decode_access_token(token)
        if payload is not None:
            email = payload.get("sub")
            if email:
                stmt = select(User).where(User.email == email)
                user = await db.scalar(stmt)
                if user:
                    return user.id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: Provide a valid JWT token or X-API-Key header",
    )



