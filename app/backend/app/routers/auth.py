"""Authentication and user administration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..logging_config import get_logger
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from ..security import create_access_token, hash_password, verify_password

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    logger.info("Login attempt | email=%s", email)
    try:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None or not verify_password(payload.password, user.password_hash):
            logger.warning("Login failed | email=%s", email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.is_active:
            logger.warning("Login blocked for inactive user | email=%s", email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        token, expires_in = create_access_token(str(user.id), user.role)
        logger.info("Login success | user=%s role=%s", user.email, user.role)
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Login error | email=%s", email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed unexpectedly")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[User]:
    users = db.scalars(select(User).order_by(User.email)).all()
    logger.debug("Listed users | count=%s", len(users))
    return list(users)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> User:
    email = payload.email.strip().lower()
    logger.info("Create user | email=%s role=%s admin=%s", email, payload.role, admin.email)
    try:
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists")

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("User created | id=%s email=%s role=%s", user.id, user.email, user.role)
        return user
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to create user | email=%s", email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user")


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> User:
    logger.info("Update user | user_id=%s admin=%s", user_id, admin.email)
    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        data = payload.model_dump(exclude_unset=True)
        if "password" in data and data["password"]:
            user.password_hash = hash_password(data.pop("password"))
        else:
            data.pop("password", None)
        for field, value in data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        logger.info("User updated | id=%s email=%s", user.id, user.email)
        return user
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to update user | user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update user")
