from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import NotificationType, Repeat
from ..logging_setup import get_logger
from ..models import Appointment, AppointmentException, Patient
from ..schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
    OccurrenceException,
)
from ..services import emit_notification

router = APIRouter(prefix="/api", tags=["appointments"])
log = get_logger("appointments")


def _get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.id == patient_id))
    if patient is None:
        log.warning("Patient %s not found", patient_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if appt is None:
        log.warning("Appointment %s not found", appointment_id)
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
    db.commit()
    db.refresh(appt)
    log.info(
        "Scheduled appointment %s for patient %s with %s (repeat=%s)",
        appt.id, patient_id, appt.provider, appt.repeat,
    )
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
    db.commit()
    db.refresh(appt)
    log.info(
        "Updated appointment %s (%s)", appt.id, "series ended" if ending else "fields"
    )
    return appt


@router.put(
    "/appointments/{appointment_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def upsert_exception(
    appointment_id: int, body: OccurrenceException, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    if appt.repeat == Repeat.NONE:
        log.warning("Rejected occurrence edit on non-recurring appointment %s", appt.id)
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
        action = "cancelled"
    elif body.start_at is not None:
        msg = (
            f"Your {when} appointment with {existing.provider or appt.provider} "
            f"was moved to {body.start_at:%b %d, %Y at %I:%M %p} UTC."
        )
        ntype = NotificationType.APPT_UPDATED
        action = "rescheduled"
    else:
        msg = f"Your {when} appointment was updated."
        ntype = NotificationType.APPT_UPDATED
        action = "updated"

    emit_notification(db, appt.patient_id, ntype, msg, appt.id)
    db.commit()
    log.info("Appointment %s: occurrence %s %s", appt.id, when, action)


@router.delete(
    "/appointments/{appointment_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revert_exception(
    appointment_id: int, at: datetime, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    existing = db.scalar(
        select(AppointmentException).where(
            AppointmentException.appointment_id == appt.id,
            AppointmentException.occurrence_start == at,
        )
    )
    if existing is None:
        log.warning("Appointment %s: no override at %s to revert", appt.id, at)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No override for that occurrence")
    db.delete(existing)
    db.commit()
    log.info("Appointment %s: occurrence %s reverted to series", appt.id, f"{at:%b %d, %Y}")


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = _get_appointment(db, appointment_id)
    emit_notification(
        db,
        appt.patient_id,
        NotificationType.APPT_CANCELLED,
        f"Appointment with {appt.provider} was cancelled.",
        appt.id,
    )
    db.delete(appt)
    db.commit()
    log.info("Deleted appointment %s (patient %s)", appointment_id, appt.patient_id)
