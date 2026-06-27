"""Bridge between the ORM and the pure recurrence engine.

Turns an Appointment (with its loaded exceptions) into concrete occurrences,
so the portal and EMR share one expansion path.
"""
from datetime import datetime

from .models import Appointment
from .recurrence import ExceptionData, Occurrence, expand_with_exceptions


def _exception_map(appt: Appointment) -> dict[datetime, ExceptionData]:
    return {
        e.occurrence_start: ExceptionData(
            cancelled=e.cancelled, provider=e.provider, start_at=e.start_at
        )
        for e in appt.exceptions
    }


def expand_appointment(
    appt: Appointment, window_start: datetime, window_end: datetime
) -> list[Occurrence]:
    return expand_with_exceptions(
        appt.start_at,
        appt.repeat,
        appt.until,
        appt.provider,
        _exception_map(appt),
        window_start,
        window_end,
    )
