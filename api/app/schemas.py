from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from pydantic.alias_generators import to_camel

from .enums import NotificationType, Repeat


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class LoginRequest(CamelModel):
    email: str
    password: str


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
    id: int
    name: str
    email: str
    dob: date | None
    phone: str | None
    appointment_count: int
    prescription_count: int
    next_appointment: datetime | None


class AppointmentCreate(CamelModel):
    provider: str = Field(min_length=1, max_length=200)
    start_at: datetime
    repeat: Repeat = Repeat.NONE
    until: date | None = None

    @model_validator(mode="after")
    def _until_after_start(self):
        if self.until is not None and self.until < self.start_at.date():
            raise ValueError("End date must be on or after the first appointment")
        return self


class AppointmentUpdate(CamelModel):
    provider: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: datetime | None = None
    repeat: Repeat | None = None
    until: date | None = None

    @model_validator(mode="after")
    def _until_after_start(self):
        if (
            self.until is not None
            and self.start_at is not None
            and self.until < self.start_at.date()
        ):
            raise ValueError("End date must be on or after the first appointment")
        return self


class AppointmentOut(CamelModel):
    id: int
    patient_id: int
    provider: str
    start_at: datetime
    repeat: Repeat
    until: date | None
    created_at: datetime


class PrescriptionCreate(CamelModel):
    medication: str
    dosage: str
    quantity: int = Field(gt=0)
    refill_on: date
    refill_schedule: Repeat = Repeat.MONTHLY
    until: date | None = None

    @model_validator(mode="after")
    def _until_after_start(self):
        if self.until is not None and self.until < self.refill_on:
            raise ValueError("End date must be on or after the first refill")
        return self


class PrescriptionUpdate(CamelModel):
    medication: str | None = None
    dosage: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    refill_on: date | None = None
    refill_schedule: Repeat | None = None
    until: date | None = None

    @model_validator(mode="after")
    def _until_after_start(self):
        if (
            self.until is not None
            and self.refill_on is not None
            and self.until < self.refill_on
        ):
            raise ValueError("End date must be on or after the first refill")
        return self


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


class PrescriptionWithNext(PrescriptionOut):
    next_refill_on: date | None = None  # computed soonest upcoming refill


class AppointmentOccurrence(CamelModel):
    appointment_id: int
    provider: str
    occurs_at: datetime
    repeat: Repeat
    overridden: bool = False


class AdminOccurrence(CamelModel):
    appointment_id: int
    occurrence_start: datetime  # original slot, used as edit id
    occurs_at: datetime         # after any reschedule
    provider: str
    repeat: Repeat
    cancelled: bool
    overridden: bool


class OccurrenceException(CamelModel):
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
    prescription_id: int
    occurrence_date: date  # original slot, used as edit id
    refill_on: date        # after any reschedule
    medication: str
    dosage: str
    quantity: int
    refill_schedule: Repeat
    cancelled: bool
    overridden: bool


class RefillException(CamelModel):
    occurrence_date: date
    cancelled: bool = False
    refill_on: date | None = None
    quantity: int | None = Field(default=None, gt=0)


class PortalSummary(CamelModel):
    patient: PatientOut
    upcoming_appointments: list[AppointmentOccurrence]
    upcoming_refills: list[RefillOccurrence]
    unread_notifications: int


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
