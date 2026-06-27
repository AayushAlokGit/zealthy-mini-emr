"""SQLAlchemy ORM models.

Recurring appointments and prescription refills are stored as *rules*
(a start + cadence + optional end), never as materialized future rows.
Concrete occurrences are computed on demand by ``recurrence.expand_occurrences``.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .db_types import UTCDateTime
from .enums import NotificationType, Repeat


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    provider: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(UTCDateTime)
    repeat: Mapped[Repeat] = mapped_column(String(16), default=Repeat.NONE)
    # Inclusive last date a recurrence may occur; None = open-ended.
    until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    exceptions: Mapped[list["AppointmentException"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )


class AppointmentException(Base):
    """A per-occurrence override of a recurring appointment (iCalendar RECURRENCE-ID).

    Identified by ``occurrence_start`` — the *original* datetime of the slot it
    overrides. ``cancelled`` removes that one occurrence; ``provider``/``start_at``
    reschedule it. Deleting the row reverts the occurrence to the series rule.
    """
    __tablename__ = "appointment_exceptions"
    __table_args__ = (
        UniqueConstraint("appointment_id", "occurrence_start", name="uq_exception_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), index=True)
    occurrence_start: Mapped[datetime] = mapped_column(UTCDateTime)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    appointment: Mapped["Appointment"] = relationship(back_populates="exceptions")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    medication: Mapped[str] = mapped_column(String(120))
    dosage: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer)
    refill_on: Mapped[date] = mapped_column(Date)
    refill_schedule: Mapped[Repeat] = mapped_column(String(16), default=Repeat.MONTHLY)
    until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")
    exceptions: Mapped[list["PrescriptionException"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan"
    )


class PrescriptionException(Base):
    """A per-occurrence override of a recurring refill (mirrors AppointmentException).

    Identified by ``occurrence_date`` — the *original* date of the refill it
    overrides. ``cancelled`` skips that refill; ``refill_on``/``quantity``
    reschedule or adjust it. Deleting the row reverts it to the series.
    """
    __tablename__ = "prescription_exceptions"
    __table_args__ = (
        UniqueConstraint("prescription_id", "occurrence_date", name="uq_rx_exception_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    occurrence_date: Mapped[date] = mapped_column(Date)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    refill_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    prescription: Mapped["Prescription"] = relationship(back_populates="exceptions")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="notifications")


class Medication(Base):
    """Lookup table seeded from data.json; powers the prescription form."""
    __tablename__ = "medications"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)


class Dosage(Base):
    __tablename__ = "dosages"

    value: Mapped[str] = mapped_column(String(40), primary_key=True)


class AuditLog(Base):
    """Append-only record of every mutation — a healthcare-grade habit."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))  # CREATE | UPDATE | DELETE
    summary: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
