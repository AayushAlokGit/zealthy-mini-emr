from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from .models import Appointment, Prescription
from .recurrence import SlotOverride, add_months, expand_slots, next_occurrence


@dataclass(frozen=True)
class ApptOccurrence:
    occurrence_start: datetime  # original slot
    effective_start: datetime   # after any reschedule
    provider: str
    cancelled: bool
    overridden: bool


@dataclass(frozen=True)
class RefillOccurrence:
    occurrence_date: date  # original slot
    refill_on: date        # after any reschedule
    quantity: int
    cancelled: bool
    overridden: bool


def _midnight(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def next_appointment_start(appt: Appointment, ref: datetime) -> datetime | None:
    """Soonest upcoming occurrence start at/after `ref`, honoring exceptions.

    One-time and exception-free series take the cheap closed-form path. Series
    with overrides are expanded over a generous window so cancelled occurrences
    are skipped and rescheduled ones surface at their new time.
    """
    if not appt.exceptions:
        return next_occurrence(appt.start_at, appt.repeat, appt.until, ref)

    upcoming = [
        occ.effective_start
        for occ in expand_appointment(appt, ref, add_months(ref, 12))
        if not occ.cancelled and occ.effective_start >= ref
    ]
    return min(upcoming) if upcoming else None


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


def next_refill_date(rx: Prescription, ref: date) -> date | None:
    """Soonest upcoming refill on/after `ref`, honoring exceptions.

    The stored `refill_on` is only the *first* refill; for a recurring series it
    drifts into the past. This returns the next refill the patient will actually
    see — skipping cancelled occurrences and following rescheduled ones.
    """
    ref_dt = _midnight(ref)
    if not rx.exceptions:
        nxt = next_occurrence(_midnight(rx.refill_on), rx.refill_schedule, rx.until, ref_dt)
        return nxt.date() if nxt else None

    upcoming = [
        occ.refill_on
        for occ in expand_prescription(rx, ref_dt, add_months(ref_dt, 12))
        if not occ.cancelled and occ.refill_on >= ref
    ]
    return min(upcoming) if upcoming else None
