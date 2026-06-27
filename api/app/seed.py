import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from .auth import hash_password
from .db import SessionLocal, init_db
from .enums import Repeat
from .logging_setup import get_logger
from .models import Appointment, Dosage, Medication, Patient, Prescription

DATA_PATH = Path(__file__).resolve().parents[2] / "data.json"
log = get_logger("seed")


def _parse_repeat(value: str | None) -> Repeat:
    if not value:
        return Repeat.NONE
    return Repeat(value.upper())


def seed() -> None:
    init_db()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        for name in data.get("medications", []):
            if db.get(Medication, name) is None:
                db.add(Medication(name=name))
        for value in data.get("dosages", []):
            if db.get(Dosage, value) is None:
                db.add(Dosage(value=value))
        db.commit()

        for u in data.get("users", []):
            patient = db.scalar(select(Patient).where(Patient.email == u["email"]))
            if patient is None:
                patient = Patient(
                    name=u["name"],
                    email=u["email"],
                    password_hash=hash_password(u["password"]),
                )
                db.add(patient)
                db.flush()

            if not patient.appointments:
                for a in u.get("appointments", []):
                    db.add(
                        Appointment(
                            patient_id=patient.id,
                            provider=a["provider"],
                            start_at=datetime.fromisoformat(a["datetime"]),
                            repeat=_parse_repeat(a.get("repeat")),
                        )
                    )
            if not patient.prescriptions:
                for p in u.get("prescriptions", []):
                    db.add(
                        Prescription(
                            patient_id=patient.id,
                            medication=p["medication"],
                            dosage=p["dosage"],
                            quantity=p["quantity"],
                            refill_on=datetime.fromisoformat(p["refill_on"]).date(),
                            refill_schedule=_parse_repeat(p.get("refill_schedule")),
                        )
                    )
            db.commit()

    log.info("Seeded database from %s", DATA_PATH.name)


def seed_if_empty() -> None:
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(Patient)) is not None:
            log.info("Database already populated; skipping seed.")
            return
    seed()


if __name__ == "__main__":
    seed()
