from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    statement = select(User).where(func.lower(User.email) == normalized_email)
    return db.scalars(statement).first()


def create_user(db: Session, email: str, password: str) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
