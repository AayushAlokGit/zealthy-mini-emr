from datetime import date, datetime, timedelta, timezone

import pytest

from app.enums import Repeat
from app.recurrence import (
    SlotOverride,
    add_months,
    expand_occurrences,
    expand_slots,
    next_occurrence,
)

UTC = timezone.utc
PDT = timezone(timedelta(hours=-7))


def dt(y, m, d, h=0, mn=0, tz=UTC):
    return datetime(y, m, d, h, mn, tzinfo=tz)


def test_add_months_simple():
    assert add_months(dt(2026, 1, 15), 1) == dt(2026, 2, 15)


def test_add_months_clamps_end_of_month():
    assert add_months(dt(2026, 1, 31), 1) == dt(2026, 2, 28)


def test_add_months_leap_year_clamp():
    assert add_months(dt(2028, 1, 31), 1) == dt(2028, 2, 29)


def test_add_months_rolls_over_year():
    assert add_months(dt(2026, 12, 10), 2) == dt(2027, 2, 10)


def test_none_in_window():
    start = dt(2026, 4, 16, 16, 30)
    out = expand_occurrences(start, Repeat.NONE, None, dt(2026, 4, 1), dt(2026, 5, 1))
    assert out == [start]


def test_none_outside_window():
    start = dt(2026, 4, 16)
    out = expand_occurrences(start, Repeat.NONE, None, dt(2026, 5, 1), dt(2026, 6, 1))
    assert out == []


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
    out = expand_occurrences(start, Repeat.WEEKLY, None, dt(2026, 4, 10), dt(2026, 4, 30))
    assert out == [dt(2026, 4, 15, 9, 0), dt(2026, 4, 22, 9, 0), dt(2026, 4, 29, 9, 0)]


def test_weekly_respects_until():
    start = dt(2026, 4, 1, 9, 0)
    out = expand_occurrences(
        start, Repeat.WEEKLY, date(2026, 4, 15), dt(2026, 4, 1), dt(2026, 5, 30)
    )
    assert out == [dt(2026, 4, 1, 9, 0), dt(2026, 4, 8, 9, 0), dt(2026, 4, 15, 9, 0)]


def test_monthly_clamps_each_month():
    start = dt(2026, 1, 31, 12, 0)
    out = expand_occurrences(start, Repeat.MONTHLY, None, dt(2026, 1, 1), dt(2026, 5, 1))
    assert out == [
        dt(2026, 1, 31, 12, 0),
        dt(2026, 2, 28, 12, 0),
        dt(2026, 3, 31, 12, 0),
        dt(2026, 4, 30, 12, 0),
    ]


def test_window_boundary_respects_offset():
    start = dt(2026, 4, 16, 16, 30, tz=PDT)
    window_start = dt(2026, 4, 16, 0, 0)
    window_end = dt(2026, 4, 17, 0, 0)
    out = expand_occurrences(start, Repeat.NONE, None, window_start, window_end)
    assert out == [start]


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


def test_reversed_window_is_empty():
    start = dt(2026, 4, 1)
    assert expand_occurrences(start, Repeat.WEEKLY, None, dt(2026, 5, 1), dt(2026, 4, 1)) == []


def test_slots_passthrough_when_no_overrides():
    start = dt(2026, 4, 1, 9, 0)
    out = expand_slots(start, Repeat.WEEKLY, None, {}, dt(2026, 4, 1), dt(2026, 4, 22))
    assert [s.effective for s in out] == [
        dt(2026, 4, 1, 9, 0),
        dt(2026, 4, 8, 9, 0),
        dt(2026, 4, 15, 9, 0),
    ]
    assert all(not s.overridden and not s.cancelled for s in out)


def test_slot_reschedules_single_occurrence():
    start = dt(2026, 4, 1, 9, 0)
    moved = {dt(2026, 4, 8, 9, 0): SlotOverride(moved_to=dt(2026, 4, 9, 14, 0))}
    out = expand_slots(start, Repeat.WEEKLY, None, moved, dt(2026, 4, 1), dt(2026, 4, 16))
    by_slot = {s.original: s for s in out}
    assert by_slot[dt(2026, 4, 8, 9, 0)].effective == dt(2026, 4, 9, 14, 0)
    assert by_slot[dt(2026, 4, 8, 9, 0)].overridden is True
    assert by_slot[dt(2026, 4, 1, 9, 0)].overridden is False


def test_slot_marks_overridden_even_without_move():
    start = dt(2026, 4, 1, 9, 0)
    ex = {dt(2026, 4, 1, 9, 0): SlotOverride()}
    out = expand_slots(start, Repeat.WEEKLY, None, ex, dt(2026, 4, 1), dt(2026, 4, 2))
    assert out[0].overridden is True and out[0].effective == dt(2026, 4, 1, 9, 0)


def test_slot_cancels_single_occurrence():
    start = dt(2026, 4, 1, 9, 0)
    ex = {dt(2026, 4, 8, 9, 0): SlotOverride(cancelled=True)}
    out = expand_slots(start, Repeat.WEEKLY, None, ex, dt(2026, 4, 1), dt(2026, 4, 16))
    cancelled = [s for s in out if s.cancelled]
    assert len(cancelled) == 1 and cancelled[0].original == dt(2026, 4, 8, 9, 0)
    assert sum(1 for s in out if not s.cancelled) == 2
