from enum import Enum


class Repeat(str, Enum):
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
