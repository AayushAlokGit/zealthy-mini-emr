"""Bridge between the ORM and the pure recurrence engine.

The system has two recurring series — appointments and prescription refills —
which share the same rule shape and the same `expand_slots` engine. Each adds
its own domain field on top (provider / quantity) and its own per-occurrence
overrides, resolved here.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from .models import Appointment, Prescription
from .recurrence import SlotOverride, expand_slots


@dataclass(frozen=True)
class ApptOccurrence:
    occurrence_start: datetime  # original slot (identity)
    effective_start: datetime   # after any reschedule
    provider: str
    cancelled: bool
    overridden: bool


@dataclass(frozen=True)
class RefillOccurrence:
    occurrence_date: date  # original slot (identity)
    refill_on: date        # after any reschedule
    quantity: int
    cancelled: bool
    overridden: bool


def _midnight(d: date) -> datetime:
    """Refills are date-based; lift to midnight UTC to flow through the engine."""
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def expand_appointment(
    appt: Appointment, window_start: datetime, window_end: datetime
) -> list[ApptOccurrence]:
    by_slot = {e.occurrence_start: e for e in appt.exceptions}
    overrides = {k: SlotOverride(e.cancelled, e.start_at) for k, e in by_slot.items()}

    out: list[ApptOccurrence] = []
    for s in expand_slots(appt.start_at, appt.repeat, appt.until, overrides, window_start, window_end):
        e = by_slot.get(s.original)
        provider = e.provider if e and e.provider else appt.provider
        out.append(ApptOccurrence(s.original, s.effective, provider, s.cancelled, s.overridden))
    return out


def expand_prescription(
    rx: Prescription, window_start: datetime, window_end: datetime
) -> list[RefillOccurrence]:
    by_slot = {_midnight(e.occurrence_date): e for e in rx.exceptions}
    overrides = {
        k: SlotOverride(e.cancelled, _midnight(e.refill_on) if e.refill_on else None)
        for k, e in by_slot.items()
    }

    out: list[RefillOccurrence] = []
    start = _midnight(rx.refill_on)
    for s in expand_slots(start, rx.refill_schedule, rx.until, overrides, window_start, window_end):
        e = by_slot.get(s.original)
        quantity = e.quantity if e and e.quantity is not None else rx.quantity
        out.append(
            RefillOccurrence(s.original.date(), s.effective.date(), quantity, s.cancelled, s.overridden)
        )
    return out
