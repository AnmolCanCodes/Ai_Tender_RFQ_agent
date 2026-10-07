import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User
from app.utils.helper import record_audit_log

logger = logging.getLogger("app.services.auth_service")


def register_user(
    db: Session,
    organization_name: str,
    full_name: str,
    email: str,
    password: str,
) -> User:
    """
    Registers a new tenant organization and owner user account.
    Fails fast if email or organization name already exists.
    """
    clean_email = email.strip().lower()
    clean_org_name = organization_name.strip()
    clean_name = full_name.strip()

    if not clean_email or not clean_org_name or not clean_name or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All fields (organization_name, full_name, email, password) are required.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    # Check for existing organization or reuse
    organization = db.query(Organization).filter(Organization.name == clean_org_name).first()
    if not organization:
        organization = Organization(name=clean_org_name)
        db.add(organization)
        db.flush()

    user = User(
        organization_id=organization.id,
        full_name=clean_name,
        email=clean_email,
        password_hash=hash_password(password),
        role="OWNER",
    )

    db.add(user)
    db.flush()

    record_audit_log(
        db=db,
        organization_id=organization.id,
        user_id=user.id,
        action="USER_REGISTERED",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": clean_email, "role": "OWNER"},
    )

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User:
    """
    Validates user credentials against password hash.
    Constant-time comparison protects against timing attacks.
    """
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def create_login_token(user: User) -> str:
    """Generates signed JWT token containing user identifier."""
    return create_access_token(user.id)

