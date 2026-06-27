from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy.orm import selectinload

from ..auth import get_current_patient
from ..db import get_db
from ..models import Appointment, Notification, Patient, Prescription
from ..occurrences import expand_appointment, expand_prescription
from ..recurrence import add_months
from ..schemas import (
    AppointmentOccurrence,
    NotificationList,
    NotificationOut,
    PortalSummary,
    PrescriptionOut,
    RefillOccurrence,
)

router = APIRouter(prefix="/api/me", tags=["portal"])

SUMMARY_DAYS = 7
DRILLDOWN_MONTHS = 3


def _active_appointments(db: Session, patient_id: int) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment)
            .where(Appointment.patient_id == patient_id, Appointment.deleted_at.is_(None))
            .options(selectinload(Appointment.exceptions))
        )
    )


def _active_prescriptions(db: Session, patient_id: int) -> list[Prescription]:
    return list(
        db.scalars(
            select(Prescription)
            .where(Prescription.patient_id == patient_id, Prescription.deleted_at.is_(None))
            .options(selectinload(Prescription.exceptions))
        )
    )


def _expand_appointments(
    appts: list[Appointment], window_start: datetime, window_end: datetime
) -> list[AppointmentOccurrence]:
    out: list[AppointmentOccurrence] = []
    for a in appts:
        for occ in expand_appointment(a, window_start, window_end):
            if occ.cancelled:
                continue
            out.append(
                AppointmentOccurrence(
                    appointment_id=a.id,
                    provider=occ.provider,
                    occurs_at=occ.effective_start,
                    repeat=a.repeat,
                    overridden=occ.overridden,
                )
            )
    out.sort(key=lambda o: o.occurs_at)
    return out


def _expand_refills(
    rxs: list[Prescription], window_start: datetime, window_end: datetime
) -> list[RefillOccurrence]:
    out: list[RefillOccurrence] = []
    for r in rxs:
        for occ in expand_prescription(r, window_start, window_end):
            if occ.cancelled:
                continue
            out.append(
                RefillOccurrence(
                    prescription_id=r.id,
                    medication=r.medication,
                    dosage=r.dosage,
                    quantity=occ.quantity,
                    refill_on=occ.refill_on,
                    refill_schedule=r.refill_schedule,
                    overridden=occ.overridden,
                )
            )
    out.sort(key=lambda o: o.refill_on)
    return out


@router.get("/summary", response_model=PortalSummary)
def summary(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=SUMMARY_DAYS)
    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    appts = _expand_appointments(_active_appointments(db, patient.id), now, window_end)
    refills = _expand_refills(_active_prescriptions(db, patient.id), day_start, window_end)
    unread_count = len(
        db.scalars(
            select(Notification.id).where(
                Notification.patient_id == patient.id, Notification.read_at.is_(None)
            )
        ).all()
    )

    return PortalSummary(
        patient=patient,
        upcoming_appointments=appts,
        upcoming_refills=refills,
        unread_notifications=unread_count,
    )


@router.get("/appointments", response_model=list[AppointmentOccurrence])
def my_appointments(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    window_end = add_months(now, DRILLDOWN_MONTHS)
    return _expand_appointments(_active_appointments(db, patient.id), now, window_end)


@router.get("/prescriptions", response_model=list[PrescriptionOut])
def my_prescriptions(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    return sorted(_active_prescriptions(db, patient.id), key=lambda r: r.refill_on)


@router.get("/refills", response_model=list[RefillOccurrence])
def my_refills(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    window_end = add_months(now, DRILLDOWN_MONTHS)
    return _expand_refills(_active_prescriptions(db, patient.id), day_start, window_end)


@router.get("/notifications", response_model=NotificationList)
def my_notifications(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    items = db.scalars(
        select(Notification)
        .where(Notification.patient_id == patient.id)
        .order_by(Notification.created_at.desc())
    ).all()
    unread = sum(1 for n in items if n.read_at is None)
    return NotificationList(
        items=[NotificationOut.model_validate(n) for n in items], unread_count=unread
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    note = db.get(Notification, notification_id)
    if note is None or note.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if note.read_at is None:
        note.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(note)
    return note


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    unread = db.scalars(
        select(Notification).where(
            Notification.patient_id == patient.id, Notification.read_at.is_(None)
        )
    ).all()
    for n in unread:
        n.read_at = now
    db.commit()
