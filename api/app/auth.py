"""Authentication: bcrypt password hashing + JWT session cookie.

The EMR (/admin) is intentionally unauthenticated per the spec. The patient
portal is gated by a signed JWT stored in an httpOnly cookie (safer than
localStorage against XSS).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Patient


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(patient_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(patient_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _patient_id_from_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def get_current_patient(
    request: Request, db: Session = Depends(get_db)
) -> Patient:
    """FastAPI dependency that resolves the logged-in patient or 401s."""
    token = request.cookies.get(settings.cookie_name)
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    if not token:
        raise unauthorized

    patient_id = _patient_id_from_token(token)
    if patient_id is None:
        raise unauthorized

    patient = db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise unauthorized
    return patient
