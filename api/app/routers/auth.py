"""Patient portal authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_patient, verify_password
from ..config import settings
from ..db import get_db
from ..logging_setup import get_logger
from ..models import Patient
from ..schemas import LoginRequest, PatientOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger("auth")


def _set_session_cookie(response: Response, patient_id: int) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=create_token(patient_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/login", response_model=PatientOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    patient = db.scalar(
        select(Patient).where(
            Patient.email == body.email, Patient.deleted_at.is_(None)
        )
    )
    if patient is None or not verify_password(body.password, patient.password_hash):
        # Log failed attempts for security monitoring (email only, never the password).
        log.warning("Failed login for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _set_session_cookie(response, patient.id)
    log.info("Patient %s logged in", patient.id)
    return patient


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(settings.cookie_name, path="/")


@router.get("/me", response_model=PatientOut)
def me(patient: Patient = Depends(get_current_patient)):
    return patient
