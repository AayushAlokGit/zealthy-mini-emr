"""Shared enums used across models, schemas, and the recurrence engine."""
from enum import Enum


class Repeat(str, Enum):
    """Recurrence cadence for appointments and prescription refills."""
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class NotificationType(str, Enum):
    APPT_SCHEDULED = "APPT_SCHEDULED"
    APPT_UPDATED = "APPT_UPDATED"
    APPT_CANCELLED = "APPT_CANCELLED"
    RX_PRESCRIBED = "RX_PRESCRIBED"
    RX_UPDATED = "RX_UPDATED"
    RX_CANCELLED = "RX_CANCELLED"
