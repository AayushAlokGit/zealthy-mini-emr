from sqlalchemy.orm import Session

from .enums import NotificationType
from .logging_setup import get_logger
from .models import AuditLog, Notification

log = get_logger("audit")


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
    log.debug("notify patient=%s type=%s", patient_id, type.value)
    return note


def record_audit(
    db: Session,
    entity: str,
    entity_id: int,
    action: str,
    summary: str,
) -> AuditLog:
    entry = AuditLog(
        entity=entity,
        entity_id=entity_id,
        action=action,
        summary=summary,
    )
    db.add(entry)
    log.info("%s %s#%s - %s", action, entity, entity_id, summary)
    return entry
