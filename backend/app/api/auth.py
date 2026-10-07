"""
Authentication endpoints: Registration, Login, and Session inspection.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, create_login_token, register_user
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Registers a new organization and owner account."""
    user = register_user(
        db=db,
        organization_name=payload.organization_name or payload.organsiation_name or "My Organization",
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticates credentials and returns signed JWT token."""
    user = authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    token = create_login_token(user)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns currently authenticated user profile."""
    return current_user
