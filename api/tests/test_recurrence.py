"""Unit tests for the pure recurrence engine."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.enums import Repeat
from app.recurrence import (
    ExceptionData,
    add_months,
    expand_occurrences,
    expand_with_exceptions,
    next_occurrence,
)

UTC = timezone.utc
# A fixed reference offset matching the seed data (-07:00).
PDT = timezone(timedelta(hours=-7))


def dt(y, m, d, h=0, mn=0, tz=UTC):
    return datetime(y, m, d, h, mn, tzinfo=tz)


# --- add_months ----------------------------------------------------------

def test_add_months_simple():
    assert add_months(dt(2026, 1, 15), 1) == dt(2026, 2, 15)


def test_add_months_clamps_end_of_month():
    # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year).
    assert add_months(dt(2026, 1, 31), 1) == dt(2026, 2, 28)


def test_add_months_leap_year_clamp():
    # Jan 31, 2028 + 1 month -> Feb 29 (2028 is a leap year).
    assert add_months(dt(2028, 1, 31), 1) == dt(2028, 2, 29)


def test_add_months_rolls_over_year():
    assert add_months(dt(2026, 12, 10), 2) == dt(2027, 2, 10)


# --- NONE (one-time) -----------------------------------------------------

def test_none_in_window():
    start = dt(2026, 4, 16, 16, 30)
    out = expand_occurrences(start, Repeat.NONE, None, dt(2026, 4, 1), dt(2026, 5, 1))
    assert out == [start]


def test_none_outside_window():
    start = dt(2026, 4, 16)
    out = expand_occurrences(start, Repeat.NONE, None, dt(2026, 5, 1), dt(2026, 6, 1))
    assert out == []


# --- WEEKLY --------------------------------------------------------------

def test_weekly_expands_across_window():
    start = dt(2026, 4, 1, 9, 0)
    out = expand_occurrences(start, Repeat.WEEKLY, None, dt(2026, 4, 1), dt(2026, 4, 30))
    assert out == [
        dt(2026, 4, 1, 9, 0),
        dt(2026, 4, 8, 9, 0),
        dt(2026, 4, 15, 9, 0),
        dt(2026, 4, 22, 9, 0),
        dt(2026, 4, 29, 9, 0),
    ]


def test_weekly_skips_before_window_start():
    start = dt(2026, 4, 1, 9, 0)
    # Window begins mid-series: the first two occurrences are excluded.
    out = expand_occurrences(start, Repeat.WEEKLY, None, dt(2026, 4, 10), dt(2026, 4, 30))
    assert out == [dt(2026, 4, 15, 9, 0), dt(2026, 4, 22, 9, 0), dt(2026, 4, 29, 9, 0)]


def test_weekly_respects_until():
    start = dt(2026, 4, 1, 9, 0)
    out = expand_occurrences(
        start, Repeat.WEEKLY, date(2026, 4, 15), dt(2026, 4, 1), dt(2026, 5, 30)
    )
    assert out == [dt(2026, 4, 1, 9, 0), dt(2026, 4, 8, 9, 0), dt(2026, 4, 15, 9, 0)]


# --- MONTHLY -------------------------------------------------------------

def test_monthly_clamps_each_month():
    start = dt(2026, 1, 31, 12, 0)
    out = expand_occurrences(start, Repeat.MONTHLY, None, dt(2026, 1, 1), dt(2026, 5, 1))
    assert out == [
        dt(2026, 1, 31, 12, 0),
        dt(2026, 2, 28, 12, 0),
        dt(2026, 3, 31, 12, 0),
        dt(2026, 4, 30, 12, 0),
    ]


# --- timezone correctness ------------------------------------------------

def test_window_boundary_respects_offset():
    # Appointment at 16:30 -07:00 == 23:30 UTC. A UTC-day window must still
    # include it, proving comparisons are offset-aware, not naive.
    start = dt(2026, 4, 16, 16, 30, tz=PDT)
    window_start = dt(2026, 4, 16, 0, 0)   # UTC midnight
    window_end = dt(2026, 4, 17, 0, 0)     # next UTC midnight
    out = expand_occurrences(start, Repeat.NONE, None, window_start, window_end)
    assert out == [start]


# --- next_occurrence -----------------------------------------------------

def test_next_occurrence_weekly():
    start = dt(2026, 4, 1, 9, 0)
    nxt = next_occurrence(start, Repeat.WEEKLY, None, ref=dt(2026, 4, 10))
    assert nxt == dt(2026, 4, 15, 9, 0)


def test_next_occurrence_none_in_future():
    start = dt(2026, 4, 20)
    assert next_occurrence(start, Repeat.NONE, None, ref=dt(2026, 4, 1)) == start


def test_next_occurrence_none_in_past_returns_none():
    start = dt(2026, 4, 1)
    assert next_occurrence(start, Repeat.NONE, None, ref=dt(2026, 4, 10)) is None


def test_next_occurrence_after_until_returns_none():
    start = dt(2026, 4, 1, 9, 0)
    nxt = next_occurrence(start, Repeat.WEEKLY, date(2026, 4, 10), ref=dt(2026, 4, 20))
    assert nxt is None


# --- edge: reversed window ----------------------------------------------

def test_reversed_window_is_empty():
    start = dt(2026, 4, 1)
    assert expand_occurrences(start, Repeat.WEEKLY, None, dt(2026, 5, 1), dt(2026, 4, 1)) == []


# --- expand_with_exceptions ---------------------------------------------

def test_exceptions_passthrough_when_none():
    start = dt(2026, 4, 1, 9, 0)
    out = expand_with_exceptions(
        start, Repeat.WEEKLY, None, "Dr A", {}, dt(2026, 4, 1), dt(2026, 4, 22)
    )
    assert [o.effective_start for o in out] == [
        dt(2026, 4, 1, 9, 0),
        dt(2026, 4, 8, 9, 0),
        dt(2026, 4, 15, 9, 0),
    ]
    assert all(not o.overridden and not o.cancelled for o in out)


def test_exception_reschedules_single_occurrence():
    start = dt(2026, 4, 1, 9, 0)
    moved = {dt(2026, 4, 8, 9, 0): ExceptionData(start_at=dt(2026, 4, 9, 14, 0))}
    out = expand_with_exceptions(
        start, Repeat.WEEKLY, None, "Dr A", moved, dt(2026, 4, 1), dt(2026, 4, 16)
    )
    by_slot = {o.occurrence_start: o for o in out}
    # The Apr 8 slot now lands on Apr 9 14:00, flagged overridden; others untouched.
    assert by_slot[dt(2026, 4, 8, 9, 0)].effective_start == dt(2026, 4, 9, 14, 0)
    assert by_slot[dt(2026, 4, 8, 9, 0)].overridden is True
    assert by_slot[dt(2026, 4, 1, 9, 0)].overridden is False


def test_exception_overrides_provider():
    start = dt(2026, 4, 1, 9, 0)
    ex = {dt(2026, 4, 1, 9, 0): ExceptionData(provider="Dr Sub")}
    out = expand_with_exceptions(
        start, Repeat.WEEKLY, None, "Dr A", ex, dt(2026, 4, 1), dt(2026, 4, 2)
    )
    assert out[0].provider == "Dr Sub"


def test_exception_cancels_single_occurrence():
    start = dt(2026, 4, 1, 9, 0)
    ex = {dt(2026, 4, 8, 9, 0): ExceptionData(cancelled=True)}
    out = expand_with_exceptions(
        start, Repeat.WEEKLY, None, "Dr A", ex, dt(2026, 4, 1), dt(2026, 4, 16)
    )
    cancelled = [o for o in out if o.cancelled]
    assert len(cancelled) == 1 and cancelled[0].occurrence_start == dt(2026, 4, 8, 9, 0)
    # The non-cancelled slots remain (a read-only consumer would filter the cancelled one).
    assert sum(1 for o in out if not o.cancelled) == 2
