"""Cross-cutting service helpers: notifications and audit logging.

Centralized so every mutation route emits consistently — no endpoint can
forget to record an audit entry or notify the patient.
"""
from sqlalchemy.orm import Session

from .enums import NotificationType
from .models import AuditLog, Notification


def emit_notification(
    db: Session,
    patient_id: int,
    type: NotificationType,
    message: str,
    related_id: int | None = None,
) -> Notification:
    """Create an in-app notification for a patient (caller commits)."""
    note = Notification(
        patient_id=patient_id,
        type=type,
        message=message,
        related_id=related_id,
    )
    db.add(note)
    return note


def record_audit(
    db: Session,
    entity: str,
    entity_id: int,
    action: str,
    summary: str,
) -> AuditLog:
    """Append an audit-log entry (caller commits)."""
    entry = AuditLog(
        entity=entity,
        entity_id=entity_id,
        action=action,
        summary=summary,
    )
    db.add(entry)
    return entry
