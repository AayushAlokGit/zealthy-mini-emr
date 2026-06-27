"""Recurrence engine.

The single source of truth for turning a stored *rule* (start + cadence +
optional end) into concrete dated occurrences inside a window. Pure functions,
no database, no I/O — so it is trivially unit-testable and reused everywhere:
the 7-day portal summary, the 3-month drill-down, and the EMR "next occurrence"
columns are all just different window arguments.

All datetimes are expected to be timezone-aware (the app stores everything in
UTC). ``until`` is an inclusive last *date* a recurrence may occur.
"""
import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .enums import Repeat

# Safety bound so an open-ended rule with a pathological window can never loop
# forever. With a >=1-week/1-month step this is far beyond any real window.
_MAX_ITERATIONS = 10_000


def add_months(dt: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day to the target month's length.

    e.g. Jan 31 + 1 month -> Feb 28 (or 29 in a leap year).
    """
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


def _nth_occurrence(start: datetime, repeat: Repeat, n: int) -> datetime:
    """The n-th occurrence (n=0 is the start itself)."""
    if repeat == Repeat.WEEKLY:
        return start + timedelta(weeks=n)
    if repeat == Repeat.MONTHLY:
        return add_months(start, n)
    return start  # NONE


def expand_occurrences(
    start: datetime,
    repeat: Repeat,
    until: date | None,
    window_start: datetime,
    window_end: datetime,
) -> list[datetime]:
    """Every concrete occurrence within the inclusive window [start, end]."""
    if window_end < window_start:
        return []

    occurrences: list[datetime] = []
    for n in range(_MAX_ITERATIONS):
        candidate = _nth_occurrence(start, repeat, n)

        if candidate > window_end:
            break
        if until is not None and candidate.date() > until:
            break
        if candidate >= window_start:
            occurrences.append(candidate)
        if repeat == Repeat.NONE:
            break

    return occurrences


@dataclass(frozen=True)
class SlotOverride:
    """A per-occurrence override of a slot, keyed externally by its original time.

    Domain-specific fields (provider, quantity, …) are applied by the caller;
    this engine only knows how to cancel a slot or move it to a new time.
    """
    cancelled: bool = False
    moved_to: datetime | None = None


@dataclass(frozen=True)
class Slot:
    original: datetime   # the original slot — stable identity for edits
    effective: datetime  # where it actually lands (after any reschedule)
    cancelled: bool
    overridden: bool


def expand_slots(
    start: datetime,
    repeat: Repeat,
    until: date | None,
    overrides: dict[datetime, SlotOverride],
    window_start: datetime,
    window_end: datetime,
) -> list[Slot]:
    """Expand a series into slots, applying single-occurrence overrides.

    Window membership is decided by each occurrence's *original* slot, so a
    rescheduled occurrence still belongs to its original week/month. Cancelled
    slots are returned with ``cancelled=True`` (callers presenting a read-only
    schedule, e.g. the portal, filter these out). Shared by appointments and
    prescription refills — each layers its own domain fields on top.
    """
    result: list[Slot] = []
    for slot in expand_occurrences(start, repeat, until, window_start, window_end):
        ov = overrides.get(slot)
        if ov is None:
            result.append(Slot(slot, slot, False, False))
        else:
            result.append(Slot(slot, ov.moved_to or slot, ov.cancelled, True))
    return result


def next_occurrence(
    start: datetime,
    repeat: Repeat,
    until: date | None,
    ref: datetime,
) -> datetime | None:
    """The first occurrence at or after ``ref``, or None if the series has ended."""
    for n in range(_MAX_ITERATIONS):
        candidate = _nth_occurrence(start, repeat, n)
        if until is not None and candidate.date() > until:
            return None
        if candidate >= ref:
            return candidate
        if repeat == Repeat.NONE:
            return None
    return None
