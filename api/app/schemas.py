"""Pydantic request/response models — the authoritative validation layer.

Responses use camelCase aliases so the JSON is idiomatic for the TypeScript
frontend, while the Python code stays snake_case. ``populate_by_name`` means
requests may use either form.
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from .enums import NotificationType, Repeat


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# --- Auth ----------------------------------------------------------------

class LoginRequest(CamelModel):
    email: str
    password: str


# --- Patients ------------------------------------------------------------

class PatientCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    dob: date | None = None
    phone: str | None = Field(default=None, max_length=50)


class PatientUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    dob: date | None = None
    phone: str | None = Field(default=None, max_length=50)


class PatientOut(CamelModel):
    id: int
    name: str
    email: str
    dob: date | None
    phone: str | None
    created_at: datetime


class PatientListItem(CamelModel):
    """Row for the EMR patient table, with at-a-glance aggregates."""
    id: int
    name: str
    email: str
    dob: date | None
    phone: str | None
    appointment_count: int
    prescription_count: int
    next_appointment: datetime | None


# --- Appointments --------------------------------------------------------

class AppointmentCreate(CamelModel):
    provider: str = Field(min_length=1, max_length=200)
    start_at: datetime
    repeat: Repeat = Repeat.NONE
    until: date | None = None


class AppointmentUpdate(CamelModel):
    provider: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: datetime | None = None
    repeat: Repeat | None = None
    until: date | None = None


class AppointmentOut(CamelModel):
    id: int
    patient_id: int
    provider: str
    start_at: datetime
    repeat: Repeat
    until: date | None
    created_at: datetime


# --- Prescriptions -------------------------------------------------------

class PrescriptionCreate(CamelModel):
    medication: str
    dosage: str
    quantity: int = Field(gt=0)
    refill_on: date
    refill_schedule: Repeat = Repeat.MONTHLY
    until: date | None = None


class PrescriptionUpdate(CamelModel):
    medication: str | None = None
    dosage: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    refill_on: date | None = None
    refill_schedule: Repeat | None = None
    until: date | None = None


class PrescriptionOut(CamelModel):
    id: int
    patient_id: int
    medication: str
    dosage: str
    quantity: int
    refill_on: date
    refill_schedule: Repeat
    until: date | None
    created_at: datetime


# --- Occurrences (computed) ---------------------------------------------

class AppointmentOccurrence(CamelModel):
    appointment_id: int
    provider: str
    occurs_at: datetime
    repeat: Repeat
    overridden: bool = False


class AdminOccurrence(CamelModel):
    """A single expanded occurrence for the EMR calendar, with edit identity."""
    appointment_id: int
    occurrence_start: datetime  # original slot — the id used to edit/revert
    occurs_at: datetime         # effective time (after any reschedule)
    provider: str
    repeat: Repeat
    cancelled: bool
    overridden: bool


class OccurrenceException(CamelModel):
    """Upsert payload to override one occurrence of a recurring appointment."""
    occurrence_start: datetime
    cancelled: bool = False
    provider: str | None = Field(default=None, max_length=200)
    start_at: datetime | None = None


class RefillOccurrence(CamelModel):
    prescription_id: int
    medication: str
    dosage: str
    quantity: int
    refill_on: date
    refill_schedule: Repeat
    overridden: bool = False


class AdminRefillOccurrence(CamelModel):
    """A single expanded refill for the EMR calendar, with edit identity."""
    prescription_id: int
    occurrence_date: date  # original slot — the id used to edit/revert
    refill_on: date        # effective date (after any reschedule)
    medication: str
    dosage: str
    quantity: int
    refill_schedule: Repeat
    cancelled: bool
    overridden: bool


class RefillException(CamelModel):
    """Upsert payload to override one refill of a recurring prescription."""
    occurrence_date: date
    cancelled: bool = False
    refill_on: date | None = None
    quantity: int | None = Field(default=None, gt=0)


# --- Portal summary ------------------------------------------------------

class PortalSummary(CamelModel):
    patient: PatientOut
    upcoming_appointments: list[AppointmentOccurrence]
    upcoming_refills: list[RefillOccurrence]
    unread_notifications: int


# --- Notifications -------------------------------------------------------

class NotificationOut(CamelModel):
    id: int
    type: NotificationType
    message: str
    related_id: int | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(CamelModel):
    items: list[NotificationOut]
    unread_count: int
