from datetime import datetime, timedelta, timezone


def _create_patient(client, email="alice@example.com", password="secret1"):
    return client.post(
        "/api/patients",
        json={"name": "Alice", "email": email, "password": password},
    )


def _future(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def _future_date(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


def _recurring_appointment(client, pid):
    return client.post(
        f"/api/patients/{pid}/appointments",
        json={"provider": "Dr Series", "startAt": _future(1), "repeat": "WEEKLY"},
    ).json()


def _recurring_prescription(client, pid):
    return client.post(
        f"/api/patients/{pid}/prescriptions",
        json={
            "medication": "Prozac",
            "dosage": "10mg",
            "quantity": 1,
            "refillOn": _future_date(1),
            "refillSchedule": "MONTHLY",
        },
    ).json()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_patient_and_login(client):
    res = _create_patient(client)
    assert res.status_code == 201
    pid = res.json()["id"]

    login = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "secret1"},
    )
    assert login.status_code == 200
    assert login.json()["id"] == pid


def test_get_and_update_patient(client):
    pid = _create_patient(client).json()["id"]
    assert client.get(f"/api/patients/{pid}").json()["email"] == "alice@example.com"

    res = client.patch(f"/api/patients/{pid}", json={"phone": "555-0000"})
    assert res.status_code == 200
    assert res.json()["phone"] == "555-0000"


def test_duplicate_email_rejected(client):
    _create_patient(client)
    dup = _create_patient(client)
    assert dup.status_code == 409


def test_login_wrong_password(client):
    _create_patient(client)
    res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "nope"},
    )
    assert res.status_code == 401


def test_unknown_medication_rejected(client):
    pid = _create_patient(client).json()["id"]
    res = client.post(
        f"/api/patients/{pid}/prescriptions",
        json={
            "medication": "FakeDrug",
            "dosage": "10mg",
            "quantity": 1,
            "refillOn": "2026-07-01",
            "refillSchedule": "MONTHLY",
        },
    )
    assert res.status_code == 422


def test_appointment_creates_notification(client):
    pid = _create_patient(client).json()["id"]
    client.post(
        f"/api/patients/{pid}/appointments",
        json={"provider": "Dr House", "startAt": "2026-07-01T15:00:00Z", "repeat": "WEEKLY"},
    )
    client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "secret1"},
    )
    notes = client.get("/api/me/notifications").json()
    assert notes["unreadCount"] == 1
    assert notes["items"][0]["type"] == "APPT_SCHEDULED"


def test_end_recurring_appointment(client):
    pid = _create_patient(client).json()["id"]
    appt = client.post(
        f"/api/patients/{pid}/appointments",
        json={"provider": "Dr House", "startAt": "2026-07-01T15:00:00Z", "repeat": "WEEKLY"},
    ).json()
    res = client.patch(f"/api/appointments/{appt['id']}", json={"until": "2026-07-15"})
    assert res.status_code == 200
    assert res.json()["until"] == "2026-07-15"


def test_delete_removes_from_list(client):
    pid = _create_patient(client).json()["id"]
    appt = client.post(
        f"/api/patients/{pid}/appointments",
        json={"provider": "Dr House", "startAt": "2026-07-01T15:00:00Z", "repeat": "NONE"},
    ).json()
    assert client.delete(f"/api/appointments/{appt['id']}").status_code == 204
    remaining = client.get(f"/api/patients/{pid}/appointments").json()
    assert remaining == []


def test_portal_requires_auth(client):
    assert client.get("/api/me/summary").status_code == 401


def test_reschedule_single_occurrence(client):
    pid = _create_patient(client).json()["id"]
    appt = _recurring_appointment(client, pid)
    schedule = client.get(f"/api/patients/{pid}/schedule").json()
    slot = schedule[0]["occurrenceStart"]
    moved = _future(2)

    res = client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": slot, "startAt": moved, "provider": "Dr Sub"},
    )
    assert res.status_code == 204

    after = {o["occurrenceStart"]: o for o in client.get(f"/api/patients/{pid}/schedule").json()}
    assert after[slot]["overridden"] is True
    assert after[slot]["provider"] == "Dr Sub"
    assert after[slot]["occursAt"][:19] == moved[:19]


def test_cancel_single_occurrence_hidden_from_portal(client):
    pid = _create_patient(client).json()["id"]
    appt = _recurring_appointment(client, pid)
    slot = client.get(f"/api/patients/{pid}/schedule").json()[0]["occurrenceStart"]

    client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": slot, "cancelled": True},
    )

    emr = {o["occurrenceStart"]: o for o in client.get(f"/api/patients/{pid}/schedule").json()}
    assert emr[slot]["cancelled"] is True

    client.post("/api/auth/login", json={"email": "alice@example.com", "password": "secret1"})
    portal = client.get("/api/me/appointments").json()
    assert all(o["occursAt"] != emr[slot]["occursAt"] for o in portal)


def test_revert_single_occurrence(client):
    pid = _create_patient(client).json()["id"]
    appt = _recurring_appointment(client, pid)
    slot = client.get(f"/api/patients/{pid}/schedule").json()[0]["occurrenceStart"]
    client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": slot, "provider": "Dr Sub"},
    )

    res = client.request("DELETE", f"/api/appointments/{appt['id']}/exceptions", params={"at": slot})
    assert res.status_code == 204
    after = {o["occurrenceStart"]: o for o in client.get(f"/api/patients/{pid}/schedule").json()}
    assert after[slot]["overridden"] is False
    assert after[slot]["provider"] == "Dr Series"


def test_cannot_edit_occurrence_of_one_time_appointment(client):
    pid = _create_patient(client).json()["id"]
    appt = client.post(
        f"/api/patients/{pid}/appointments",
        json={"provider": "Dr Once", "startAt": _future(1), "repeat": "NONE"},
    ).json()
    res = client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": _future(1), "cancelled": True},
    )
    assert res.status_code == 422


def test_next_appointment_skips_cancelled_occurrence(client):
    pid = _create_patient(client).json()["id"]
    appt = _recurring_appointment(client, pid)
    schedule = client.get(f"/api/patients/{pid}/schedule").json()
    first, second = schedule[0], schedule[1]

    listed = {p["id"]: p for p in client.get("/api/patients").json()}[pid]
    assert listed["nextAppointment"][:19] == first["occursAt"][:19]

    client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": first["occurrenceStart"], "cancelled": True},
    )

    listed = {p["id"]: p for p in client.get("/api/patients").json()}[pid]
    assert listed["nextAppointment"][:19] == second["occursAt"][:19]


def test_next_appointment_reflects_rescheduled_occurrence(client):
    pid = _create_patient(client).json()["id"]
    appt = _recurring_appointment(client, pid)
    slot = client.get(f"/api/patients/{pid}/schedule").json()[0]["occurrenceStart"]
    moved = _future(2)

    client.put(
        f"/api/appointments/{appt['id']}/exceptions",
        json={"occurrenceStart": slot, "startAt": moved},
    )

    listed = {p["id"]: p for p in client.get("/api/patients").json()}[pid]
    assert listed["nextAppointment"][:19] == moved[:19]


def test_reschedule_single_refill(client):
    pid = _create_patient(client).json()["id"]
    rx = _recurring_prescription(client, pid)
    slot = client.get(f"/api/patients/{pid}/refill-schedule").json()[0]["occurrenceDate"]
    moved = _future_date(3)

    res = client.put(
        f"/api/prescriptions/{rx['id']}/exceptions",
        json={"occurrenceDate": slot, "refillOn": moved, "quantity": 5},
    )
    assert res.status_code == 204

    after = {o["occurrenceDate"]: o for o in client.get(f"/api/patients/{pid}/refill-schedule").json()}
    assert after[slot]["overridden"] is True
    assert after[slot]["refillOn"] == moved
    assert after[slot]["quantity"] == 5


def test_cancel_single_refill_hidden_from_portal(client):
    pid = _create_patient(client).json()["id"]
    rx = _recurring_prescription(client, pid)
    slot = client.get(f"/api/patients/{pid}/refill-schedule").json()[0]["occurrenceDate"]

    client.put(
        f"/api/prescriptions/{rx['id']}/exceptions",
        json={"occurrenceDate": slot, "cancelled": True},
    )

    emr = {o["occurrenceDate"]: o for o in client.get(f"/api/patients/{pid}/refill-schedule").json()}
    assert emr[slot]["cancelled"] is True

    client.post("/api/auth/login", json={"email": "alice@example.com", "password": "secret1"})
    portal = client.get("/api/me/refills").json()
    assert all(o["refillOn"] != slot for o in portal)


def test_revert_single_refill(client):
    pid = _create_patient(client).json()["id"]
    rx = _recurring_prescription(client, pid)
    slot = client.get(f"/api/patients/{pid}/refill-schedule").json()[0]["occurrenceDate"]
    client.put(
        f"/api/prescriptions/{rx['id']}/exceptions",
        json={"occurrenceDate": slot, "quantity": 9},
    )

    res = client.request("DELETE", f"/api/prescriptions/{rx['id']}/exceptions", params={"at": slot})
    assert res.status_code == 204
    after = {o["occurrenceDate"]: o for o in client.get(f"/api/patients/{pid}/refill-schedule").json()}
    assert after[slot]["overridden"] is False
    assert after[slot]["quantity"] == 1


def test_cannot_edit_refill_of_one_time_prescription(client):
    pid = _create_patient(client).json()["id"]
    rx = client.post(
        f"/api/patients/{pid}/prescriptions",
        json={
            "medication": "Prozac",
            "dosage": "10mg",
            "quantity": 1,
            "refillOn": _future_date(1),
            "refillSchedule": "NONE",
        },
    ).json()
    res = client.put(
        f"/api/prescriptions/{rx['id']}/exceptions",
        json={"occurrenceDate": _future_date(1), "cancelled": True},
    )
    assert res.status_code == 422
