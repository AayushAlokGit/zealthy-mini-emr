"""Prescription CRUD. Medication and dosage are validated against the seeded
lookup tables so the form can never persist an unknown value."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import NotificationType, Repeat
from ..models import Dosage, Medication, Patient, Prescription, PrescriptionException
from ..schemas import (
    PrescriptionCreate,
    PrescriptionOut,
    PrescriptionUpdate,
    RefillException,
)
from ..services import emit_notification, record_audit

router = APIRouter(prefix="/api", tags=["prescriptions"])


def _get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.scalar(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


def _get_prescription(db: Session, prescription_id: int) -> Prescription:
    rx = db.scalar(
        select(Prescription).where(
            Prescription.id == prescription_id, Prescription.deleted_at.is_(None)
        )
    )
    if rx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    return rx


def _validate_lookups(db: Session, medication: str | None, dosage: str | None) -> None:
    if medication is not None and db.get(Medication, medication) is None:
        raise HTTPException(
            422, f"Unknown medication: {medication}"
        )
    if dosage is not None and db.get(Dosage, dosage) is None:
        raise HTTPException(
            422, f"Unknown dosage: {dosage}"
        )


@router.post(
    "/patients/{patient_id}/prescriptions",
    response_model=PrescriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_prescription(
    patient_id: int, body: PrescriptionCreate, db: Session = Depends(get_db)
):
    _get_patient(db, patient_id)
    _validate_lookups(db, body.medication, body.dosage)
    rx = Prescription(
        patient_id=patient_id,
        medication=body.medication,
        dosage=body.dosage,
        quantity=body.quantity,
        refill_on=body.refill_on,
        refill_schedule=body.refill_schedule,
        until=body.until,
    )
    db.add(rx)
    db.flush()
    emit_notification(
        db,
        patient_id,
        NotificationType.RX_PRESCRIBED,
        f"New prescription: {rx.medication} {rx.dosage}, refill on {rx.refill_on}.",
        related_id=rx.id,
    )
    record_audit(db, "prescription", rx.id, "CREATE", f"Prescribed {rx.medication} {rx.dosage}")
    db.commit()
    db.refresh(rx)
    return rx


@router.patch("/prescriptions/{prescription_id}", response_model=PrescriptionOut)
def update_prescription(
    prescription_id: int, body: PrescriptionUpdate, db: Session = Depends(get_db)
):
    rx = _get_prescription(db, prescription_id)
    data = body.model_dump(exclude_unset=True)
    _validate_lookups(db, data.get("medication"), data.get("dosage"))
    for field, value in data.items():
        setattr(rx, field, value)

    msg = f"Prescription {rx.medication} {rx.dosage} was updated."
    emit_notification(db, rx.patient_id, NotificationType.RX_UPDATED, msg, rx.id)
    record_audit(db, "prescription", rx.id, "UPDATE", msg)
    db.commit()
    db.refresh(rx)
    return rx


@router.put(
    "/prescriptions/{prescription_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def upsert_refill_exception(
    prescription_id: int, body: RefillException, db: Session = Depends(get_db)
):
    """Override a single refill: reschedule (refill_on/quantity) or skip it."""
    rx = _get_prescription(db, prescription_id)
    if rx.refill_schedule == Repeat.NONE:
        raise HTTPException(422, "Only recurring refills have occurrences to edit")

    existing = db.scalar(
        select(PrescriptionException).where(
            PrescriptionException.prescription_id == rx.id,
            PrescriptionException.occurrence_date == body.occurrence_date,
        )
    )
    if existing is None:
        existing = PrescriptionException(
            prescription_id=rx.id, occurrence_date=body.occurrence_date
        )
        db.add(existing)
    existing.cancelled = body.cancelled
    existing.refill_on = body.refill_on
    existing.quantity = body.quantity

    when = f"{body.occurrence_date:%b %d, %Y}"
    if body.cancelled:
        msg = f"Your {when} {rx.medication} refill was skipped."
        ntype = NotificationType.RX_CANCELLED
    else:
        parts = []
        if body.refill_on is not None:
            parts.append(f"moved to {body.refill_on:%b %d, %Y}")
        if body.quantity is not None:
            parts.append(f"quantity {body.quantity}")
        change = ", ".join(parts) if parts else "updated"
        msg = f"Your {when} {rx.medication} refill was {change}."
        ntype = NotificationType.RX_UPDATED

    emit_notification(db, rx.patient_id, ntype, msg, rx.id)
    record_audit(db, "prescription", rx.id, "UPDATE", f"Refill {when}: {msg}")
    db.commit()


@router.delete(
    "/prescriptions/{prescription_id}/exceptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revert_refill_exception(
    prescription_id: int, at: date, db: Session = Depends(get_db)
):
    """Revert a single refill back to the series schedule (delete its override)."""
    rx = _get_prescription(db, prescription_id)
    existing = db.scalar(
        select(PrescriptionException).where(
            PrescriptionException.prescription_id == rx.id,
            PrescriptionException.occurrence_date == at,
        )
    )
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No override for that refill")
    db.delete(existing)
    record_audit(db, "prescription", rx.id, "UPDATE", f"Refill {at:%b %d, %Y} reverted to series")
    db.commit()


@router.delete("/prescriptions/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(prescription_id: int, db: Session = Depends(get_db)):
    rx = _get_prescription(db, prescription_id)
    rx.deleted_at = datetime.now(timezone.utc)
    emit_notification(
        db,
        rx.patient_id,
        NotificationType.RX_CANCELLED,
        f"Prescription {rx.medication} {rx.dosage} was discontinued.",
        rx.id,
    )
    record_audit(db, "prescription", rx.id, "DELETE", f"Discontinued {rx.medication}")
    db.commit()
