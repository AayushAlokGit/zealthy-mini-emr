"""End-to-end API tests covering the core EMR + portal flows."""


def _create_patient(client, email="alice@example.com", password="secret1"):
    return client.post(
        "/api/patients",
        json={"name": "Alice", "email": email, "password": password},
    )


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_patient_and_login(client):
    """A patient created via the EMR can log in to the portal (key spec rule)."""
    res = _create_patient(client)
    assert res.status_code == 201
    pid = res.json()["id"]

    login = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "secret1"},
    )
    assert login.status_code == 200
    assert login.json()["id"] == pid


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


def test_soft_delete_removes_from_list(client):
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
