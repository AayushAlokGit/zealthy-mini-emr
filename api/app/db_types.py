"""Custom SQLAlchemy types.

SQLite has no native timezone-aware datetime: it silently drops tzinfo on write
and returns naive datetimes on read. Since our recurrence math must be correct
across the ``-07:00`` offsets in the seed data, we normalize every datetime to
UTC on the way in and re-attach UTC on the way out. The rest of the app can then
assume all datetimes from the DB are tz-aware UTC.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            # Treat naive input as already-UTC rather than guessing local time.
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)
