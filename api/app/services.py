from sqlalchemy.orm import Session

from .enums import NotificationType
from .models import Notification


def emit_notification(
    db: Session,
    patient_id: int,
    type: NotificationType,
    message: str,
    related_id: int | None = None,
) -> Notification:
    note = Notification(
        patient_id=patient_id,
        type=type,
        message=message,
        related_id=related_id,
    )
    db.add(note)
    return note
