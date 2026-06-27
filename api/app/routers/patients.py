"""EMR patient management: list (with at-a-glance aggregates), create, read, update.

No delete — the spec calls for CRU on patients.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import hash_password
from ..db import get_db
from ..models import Appointment, Patient, Prescription
from ..recurrence import next_occurrence
from ..schemas import (
    AppointmentOut,
    PatientCreate,
    PatientListItem,
    PatientOut,
    PatientUpdate,
    PrescriptionOut,
)
from ..services import record_audit

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _active(query):
    return query.where(Patient.deleted_at.is_(None))


@router.get("", response_model=list[PatientListItem])
def list_patients(db: Session = Depends(get_db)):
    patients = db.scalars(
        _active(select(Patient))
        .options(selectinload(Patient.appointments), selectinload(Patient.prescriptions))
        .order_by(Patient.name)
    ).all()

    now = datetime.now(timezone.utc)
    rows: list[PatientListItem] = []
    for p in patients:
        appts = [a for a in p.appointments if a.deleted_at is None]
        rx = [r for r in p.prescriptions if r.deleted_at is None]

        # Earliest upcoming occurrence across all of the patient's appointments.
        next_appt = None
        for a in appts:
            nxt = next_occurrence(a.start_at, a.repeat, a.until, now)
            if nxt and (next_appt is None or nxt < next_appt):
                next_appt = nxt

        rows.append(
            PatientListItem(
                id=p.id,
                name=p.name,
                email=p.email,
                dob=p.dob,
                phone=p.phone,
                appointment_count=len(appts),
                prescription_count=len(rx),
                next_appointment=next_appt,
            )
        )
    return rows


def _get_active_patient(db: Session, patient_id: int) -> Patient:
    patient = db.scalar(_active(select(Patient)).where(Patient.id == patient_id))
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Patient).where(Patient.email == body.email))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    patient = Patient(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        dob=body.dob,
        phone=body.phone,
    )
    db.add(patient)
    db.flush()
    record_audit(db, "patient", patient.id, "CREATE", f"Created patient {patient.name}")
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return _get_active_patient(db, patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, body: PatientUpdate, db: Session = Depends(get_db)):
    patient = _get_active_patient(db, patient_id)

    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != patient.email:
        clash = db.scalar(select(Patient).where(Patient.email == data["email"]))
        if clash is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    if "password" in data:
        patient.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(patient, field, value)

    record_audit(db, "patient", patient.id, "UPDATE", f"Updated patient {patient.name}")
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}/appointments", response_model=list[AppointmentOut])
def list_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    _get_active_patient(db, patient_id)
    return db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient_id, Appointment.deleted_at.is_(None))
        .order_by(Appointment.start_at)
    ).all()


@router.get("/{patient_id}/prescriptions", response_model=list[PrescriptionOut])
def list_patient_prescriptions(patient_id: int, db: Session = Depends(get_db)):
    _get_active_patient(db, patient_id)
    return db.scalars(
        select(Prescription)
        .where(Prescription.patient_id == patient_id, Prescription.deleted_at.is_(None))
        .order_by(Prescription.refill_on)
    ).all()
