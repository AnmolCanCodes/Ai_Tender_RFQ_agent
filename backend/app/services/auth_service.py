from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User


def register_user(
    db: Session,
    organization_name: str,
    full_name: str,
    email: str,
    password: str
):
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    organization = Organization(
        name=organization_name
    )

    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role="OWNER"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str
):
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    return user


def create_login_token(user: User):
    return create_access_token(user.id, user.organization_id)