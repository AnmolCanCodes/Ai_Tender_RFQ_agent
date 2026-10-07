from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    MVP-friendly authentication: Returns user if token is valid,
    or creates a demo user if no token provided (for local development).
    """
    if not token:
        # Create or return demo user for local development
        demo_user = db.query(User).filter(User.email == "demo@local.dev").first()
        if not demo_user:
            from app.models.organization import Organization
            from app.core.security import hash_password
            demo_org = db.query(Organization).filter(Organization.name == "demo_org_1").first()
            if not demo_org:
                demo_org = Organization(name="demo_org_1")
                db.add(demo_org)
                db.flush()
            demo_user = User(
                organization_id=demo_org.id,
                full_name="Demo User",
                email="demo@local.dev",
                password_hash=hash_password("demo123"),
                role="OWNER",
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user

    try:
        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = db.get(User, int(user_id))

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def get_current_organization_id(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> int:
    """
    Returns the organization ID from the current user.
    For MVP/demo mode, defaults to demo_org_1 if user lacks organization.
    """
    if not current_user.organization_id:
        from app.models.organization import Organization
        demo_org = db.query(Organization).filter(Organization.name == "demo_org_1").first()
        if not demo_org:
            demo_org = Organization(name="demo_org_1")
            db.add(demo_org)
            db.flush()
        return demo_org.id
    return current_user.organization_id