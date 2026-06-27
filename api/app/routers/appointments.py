"""Appointment CRUD. Recurring appointments are stored as rules; "ending" a
series sets ``until`` rather than deleting history."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import NotificationType, Repeat
from ..models import Appointment, AppointmentException, Patient
from ..schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
    OccurrenceException,
)
from ..services import emit_notification, record_audit

router = APIRouter(prefix="/api", tags=["appointments"])


def _get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.scalar(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id, Appointment.deleted_at.is_(None)
        )
    )
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    return appt


@router.post(
    "/patients/{patient_id}/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    patient_id: int, body: AppointmentCreate, db: Session = Depends(get_db)
):
    _get_patient(db, patient_id)
    appt = Appointment(
        patient_id=patient_id,
        provider=body.provider,
        start_at=body.start_at,
        repeat=body.repeat,
        until=body.until,
    )
    db.add(appt)
    db.flush()
    emit_notification(
        db,
        patient_id,
        NotificationType.APPT_SCHEDULED,
        f"New appointment with {appt.provider} on {appt.start_at:%b %d, %Y at %I:%M %p} UTC.",
        related_id=appt.id,
    )
    record_audit(db, "appointment", appt.id, "CREATE", f"Booked with {appt.provider}")
    db.commit()
    db.refresh(appt)
    return appt


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: int, body: AppointmentUpdate, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    data = body.model_dump(exclude_unset=True)
    ending = "until" in data and data["until"] is not None
    for field, value in data.items():
        setattr(appt, field, value)

    msg = (
        f"Recurring appointment with {appt.provider} ends {data['until']}."
        if ending
        else f"Appointment with {appt.provider} was updated."
    )
    emit_notification(db, appt.patient_id, NotificationType.APPT_UPDATED, msg, appt.id)
    record_audit(db, "appointment", appt.id, "UPDATE", msg)
    db.commit()
    db.refresh(appt)
    return appt


@router.put(
    "/appointments/{appointment_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def upsert_exception(
    appointment_id: int, body: OccurrenceException, db: Session = Depends(get_db)
):
    """Override a single occurrence: reschedule (start_at/provider) or cancel it."""
    appt = _get_appointment(db, appointment_id)
    if appt.repeat == Repeat.NONE:
        raise HTTPException(422, "Only recurring appointments have occurrences to edit")

    existing = db.scalar(
        select(AppointmentException).where(
            AppointmentException.appointment_id == appt.id,
            AppointmentException.occurrence_start == body.occurrence_start,
        )
    )
    if existing is None:
        existing = AppointmentException(
            appointment_id=appt.id, occurrence_start=body.occurrence_start
        )
        db.add(existing)
    existing.cancelled = body.cancelled
    existing.provider = body.provider
    existing.start_at = body.start_at

    when = f"{body.occurrence_start:%b %d, %Y}"
    if body.cancelled:
        msg = f"Your {when} appointment with {appt.provider} was cancelled."
        ntype = NotificationType.APPT_CANCELLED
    elif body.start_at is not None:
        msg = (
            f"Your {when} appointment with {existing.provider or appt.provider} "
            f"was moved to {body.start_at:%b %d, %Y at %I:%M %p} UTC."
        )
        ntype = NotificationType.APPT_UPDATED
    else:
        msg = f"Your {when} appointment was updated."
        ntype = NotificationType.APPT_UPDATED

    emit_notification(db, appt.patient_id, ntype, msg, appt.id)
    record_audit(db, "appointment", appt.id, "UPDATE", f"Occurrence {when}: {msg}")
    db.commit()


@router.delete(
    "/appointments/{appointment_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revert_exception(
    appointment_id: int, at: datetime, db: Session = Depends(get_db)
):
    """Revert a single occurrence back to the series rule (delete its override)."""
    appt = _get_appointment(db, appointment_id)
    existing = db.scalar(
        select(AppointmentException).where(
            AppointmentException.appointment_id == appt.id,
            AppointmentException.occurrence_start == at,
        )
    )
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No override for that occurrence")
    db.delete(existing)
    record_audit(
        db, "appointment", appt.id, "UPDATE", f"Occurrence {at:%b %d, %Y} reverted to series"
    )
    db.commit()


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = _get_appointment(db, appointment_id)
    appt.deleted_at = datetime.now(timezone.utc)
    emit_notification(
        db,
        appt.patient_id,
        NotificationType.APPT_CANCELLED,
        f"Appointment with {appt.provider} was cancelled.",
        appt.id,
    )
    record_audit(db, "appointment", appt.id, "DELETE", f"Cancelled with {appt.provider}")
    db.commit()
