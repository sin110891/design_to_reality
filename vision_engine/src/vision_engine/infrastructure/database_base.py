from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata for all Vision Engine bounded contexts."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
