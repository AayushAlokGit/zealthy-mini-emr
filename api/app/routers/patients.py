from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import hash_password
from ..db import get_db
from ..logging_setup import get_logger
from ..models import Appointment, Patient, Prescription
from ..occurrences import (
    expand_appointment,
    expand_prescription,
    next_appointment_start,
    next_refill_date,
)
from ..recurrence import add_months
from ..schemas import (
    AdminOccurrence,
    AdminRefillOccurrence,
    AppointmentOut,
    PatientCreate,
    PatientListItem,
    PatientOut,
    PatientUpdate,
    PrescriptionWithNext,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])
log = get_logger("patients")


@router.get("", response_model=list[PatientListItem])
def list_patients(db: Session = Depends(get_db)):
    patients = db.scalars(
        select(Patient)
        .options(
            selectinload(Patient.appointments).selectinload(Appointment.exceptions),
            selectinload(Patient.prescriptions),
        )
        .order_by(Patient.name)
    ).all()

    now = datetime.now(timezone.utc)
    rows: list[PatientListItem] = []
    for p in patients:
        appts = p.appointments
        rx = p.prescriptions

        next_appt = None
        for a in appts:
            nxt = next_appointment_start(a, now)
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


def _get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.id == patient_id))
    if patient is None:
        log.warning("Patient %s not found", patient_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Patient).where(Patient.email == body.email))
    if exists is not None:
        log.warning("Rejected patient create: email already in use (%s)", body.email)
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    patient = Patient(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        dob=body.dob,
        phone=body.phone,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    log.info("Created patient %s (%s)", patient.id, patient.email)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return _get_patient(db, patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, body: PatientUpdate, db: Session = Depends(get_db)):
    patient = _get_patient(db, patient_id)

    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != patient.email:
        clash = db.scalar(select(Patient).where(Patient.email == data["email"]))
        if clash is not None:
            log.warning("Rejected patient %s update: email already in use", patient_id)
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    if "password" in data:
        patient.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    log.info("Updated patient %s (fields: %s)", patient.id, ", ".join(data) or "none")
    return patient


@router.get("/{patient_id}/appointments", response_model=list[AppointmentOut])
def list_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    _get_patient(db, patient_id)
    return db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.start_at)
    ).all()


@router.get("/{patient_id}/schedule", response_model=list[AdminOccurrence])
def patient_schedule(
    patient_id: int,
    months: int = Query(default=3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    _get_patient(db, patient_id)
    appts = db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .options(selectinload(Appointment.exceptions))
    ).all()

    now = datetime.now(timezone.utc)
    window_end = add_months(now, months)
    rows: list[AdminOccurrence] = []
    for a in appts:
        for occ in expand_appointment(a, now, window_end):
            rows.append(
                AdminOccurrence(
                    appointment_id=a.id,
                    occurrence_start=occ.occurrence_start,
                    occurs_at=occ.effective_start,
                    provider=occ.provider,
                    repeat=a.repeat,
                    cancelled=occ.cancelled,
                    overridden=occ.overridden,
                )
            )
    rows.sort(key=lambda r: r.occurs_at)
    return rows


@router.get("/{patient_id}/refill-schedule", response_model=list[AdminRefillOccurrence])
def patient_refill_schedule(
    patient_id: int,
    months: int = Query(default=3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    _get_patient(db, patient_id)
    rxs = db.scalars(
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .options(selectinload(Prescription.exceptions))
    ).all()

    now = datetime.now(timezone.utc)
    window_end = add_months(now, months)
    rows: list[AdminRefillOccurrence] = []
    for r in rxs:
        for occ in expand_prescription(r, now, window_end):
            rows.append(
                AdminRefillOccurrence(
                    prescription_id=r.id,
                    occurrence_date=occ.occurrence_date,
                    refill_on=occ.refill_on,
                    medication=r.medication,
                    dosage=r.dosage,
                    quantity=occ.quantity,
                    refill_schedule=r.refill_schedule,
                    cancelled=occ.cancelled,
                    overridden=occ.overridden,
                )
            )
    rows.sort(key=lambda r: r.refill_on)
    return rows


@router.get("/{patient_id}/prescriptions", response_model=list[PrescriptionWithNext])
def list_patient_prescriptions(patient_id: int, db: Session = Depends(get_db)):
    _get_patient(db, patient_id)
    rxs = db.scalars(
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .options(selectinload(Prescription.exceptions))
        .order_by(Prescription.refill_on)
    ).all()

    today = datetime.now(timezone.utc).date()
    items = []
    for r in rxs:
        item = PrescriptionWithNext.model_validate(r)
        item.next_refill_on = next_refill_date(r, today)
        items.append(item)
    return items
