import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .enums import Repeat

_MAX_ITERATIONS = 10_000


def add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


def _nth_occurrence(start: datetime, repeat: Repeat, n: int) -> datetime:
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
    cancelled: bool = False
    moved_to: datetime | None = None


@dataclass(frozen=True)
class Slot:
    original: datetime
    effective: datetime  # after any reschedule
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
    for n in range(_MAX_ITERATIONS):
        candidate = _nth_occurrence(start, repeat, n)
        if until is not None and candidate.date() > until:
            return None
        if candidate >= ref:
            return candidate
        if repeat == Repeat.NONE:
            return None
    return None
