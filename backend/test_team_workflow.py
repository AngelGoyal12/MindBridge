"""Tests for the Main Coordinator -> Department Coordinator -> Staff workflow.

Covers staff-level task assignment and claiming, the Main Coordinator's
redacted task oversight, and internal messaging between the Main Coordinator,
Department Coordinators and departments.
"""

import pytest

from test_auth import _create_test_user, _login_and_get_csrf
from test_tasks import _submit_case


def _as(test_client, email):
    """Log in as a user and return that session's CSRF token."""
    return _login_and_get_csrf(test_client, email)


@pytest.fixture
def team(test_client, test_student):
    case = _submit_case(test_client, test_student)
    ids = {
        "coordinator": _create_test_user(
            "coordinator", "coord@example.com", name="Case Coordinator"
        ),
        "asha": _create_test_user(
            "department_staff", "asha@example.com",
            name="Asha Counsellor", department="Counselling",
        ),
        "bela": _create_test_user(
            "department_staff", "bela@example.com",
            name="Bela Counsellor", department="Counselling",
        ),
        "chitra": _create_test_user(
            "department_staff", "chitra@example.com",
            name="Chitra Accounts", department="Accounts",
        ),
        "admin": _create_test_user(
            "admin", "main@example.com", name="Main Admin"
        ),
        "other_coordinator": _create_test_user(
            "coordinator", "other-coord@example.com", name="Other Coordinator"
        ),
    }
    csrf = _as(test_client, "main@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": ids["coordinator"]},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    return {"case": case, "ids": ids}


def _admin_task(test_client, case_id, **overrides):
    csrf = _as(test_client, "main@example.com")
    payload = {
        "department": "Counselling",
        "title": "Offer a counselling session",
        "instructions": "Reach out and offer a first session this week.",
    }
    payload.update(overrides)
    return test_client.post(
        f"/api/v1/admin/cases/{case_id}/tasks",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )


# ---------------------------------------------------------------- tasks


def test_main_coordinator_sends_task_and_coordinator_assigns_staff(
    test_client, team
):
    case_id = team["case"]["id"]
    created = _admin_task(test_client, case_id, department="counselling")
    assert created.status_code == 201
    task = created.json()["task"]
    assert task["department"] == "Counselling"
    assert task["assigned_staff_id"] is None

    # The student only ever sees a generic progress update.
    _as(test_client, "student@college.example.edu.in")
    updates = test_client.get(f"/api/v1/cases/{case_id}").json()["progress_updates"]
    assert any(u["title"] == "Support task assigned" for u in updates)
    assert not any("first session" in u["message"] for u in updates)

    # The Department Coordinator hands it to one staff member.
    csrf = _as(test_client, "coord@example.com")
    assigned = test_client.patch(
        f"/api/v1/coordinator/tasks/{task['id']}/assignee",
        json={"staff_id": team["ids"]["asha"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert assigned.status_code == 200
    body = assigned.json()["task"]
    assert body["assigned_staff_id"] == team["ids"]["asha"]
    assert body["assigned_staff_name"] == "Asha Counsellor"
    assert body["events"][-1]["note"] == "Assigned to Asha Counsellor."

    # Only that staff member sees it; a colleague does not.
    _as(test_client, "bela@example.com")
    assert test_client.get("/api/v1/department/tasks").json() == []
    assert test_client.get(
        f"/api/v1/department/tasks/{task['id']}"
    ).status_code == 404

    bela_csrf = _as(test_client, "bela@example.com")
    assert test_client.patch(
        f"/api/v1/department/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": bela_csrf},
    ).status_code == 404

    asha_csrf = _as(test_client, "asha@example.com")
    mine = test_client.get("/api/v1/department/tasks").json()
    assert [t["id"] for t in mine] == [task["id"]]
    assert mine[0]["assigned_to_me"] is True
    summary = test_client.get("/api/v1/department/tasks/summary").json()
    assert summary["mine"] == 1 and summary["unassigned"] == 0
    assert test_client.patch(
        f"/api/v1/department/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": asha_csrf},
    ).status_code == 200


def test_task_cannot_be_assigned_to_staff_of_another_department(
    test_client, team
):
    task = _admin_task(test_client, team["case"]["id"]).json()["task"]
    csrf = _as(test_client, "coord@example.com")
    response = test_client.patch(
        f"/api/v1/coordinator/tasks/{task['id']}/assignee",
        json={"staff_id": team["ids"]["chitra"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 400


def test_task_can_be_created_already_assigned_and_returned_to_pool(
    test_client, team
):
    created = _admin_task(
        test_client, team["case"]["id"],
        assigned_staff_id=team["ids"]["bela"],
    )
    assert created.status_code == 201
    task = created.json()["task"]
    assert task["assigned_staff_name"] == "Bela Counsellor"

    csrf = _as(test_client, "main@example.com")
    released = test_client.patch(
        f"/api/v1/admin/tasks/{task['id']}/assignee",
        json={"staff_id": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert released.status_code == 200
    assert released.json()["task"]["assigned_staff_id"] is None


def test_completed_task_cannot_be_reassigned(test_client, team):
    task = _admin_task(
        test_client, team["case"]["id"],
        assigned_staff_id=team["ids"]["asha"],
    ).json()["task"]
    csrf = _as(test_client, "asha@example.com")
    assert test_client.patch(
        f"/api/v1/department/tasks/{task['id']}/status",
        json={"status": "completed", "note": "Session booked."},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    csrf = _as(test_client, "coord@example.com")
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{task['id']}/assignee",
        json={"staff_id": team["ids"]["bela"]},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 409


def test_staff_claim_from_department_pool_is_exclusive(test_client, team):
    task = _admin_task(test_client, team["case"]["id"]).json()["task"]

    # Both counselling staff can see the unclaimed task; accounts cannot.
    _as(test_client, "bela@example.com")
    assert [t["id"] for t in test_client.get("/api/v1/department/tasks").json()] == [
        task["id"]
    ]
    _as(test_client, "chitra@example.com")
    assert test_client.get("/api/v1/department/tasks").json() == []

    asha_csrf = _as(test_client, "asha@example.com")
    claimed = test_client.post(
        f"/api/v1/department/tasks/{task['id']}/claim",
        headers={"X-CSRF-Token": asha_csrf},
    )
    assert claimed.status_code == 200
    assert claimed.json()["task"]["assigned_to_me"] is True
    assert claimed.json()["task"]["events"][-1]["note"] == "Claimed by Asha Counsellor."
    # Claiming twice is refused.
    assert test_client.post(
        f"/api/v1/department/tasks/{task['id']}/claim",
        headers={"X-CSRF-Token": asha_csrf},
    ).status_code == 409

    # The colleague no longer sees it and cannot claim it.
    bela_csrf = _as(test_client, "bela@example.com")
    assert test_client.get("/api/v1/department/tasks").json() == []
    assert test_client.post(
        f"/api/v1/department/tasks/{task['id']}/claim",
        headers={"X-CSRF-Token": bela_csrf},
    ).status_code == 404


def test_claim_requires_csrf_and_staff_role(test_client, team):
    task = _admin_task(test_client, team["case"]["id"]).json()["task"]
    _as(test_client, "asha@example.com")
    assert test_client.post(
        f"/api/v1/department/tasks/{task['id']}/claim"
    ).status_code == 403
    coordinator_csrf = _as(test_client, "coord@example.com")
    assert test_client.post(
        f"/api/v1/department/tasks/{task['id']}/claim",
        headers={"X-CSRF-Token": coordinator_csrf},
    ).status_code == 403


def test_working_on_a_pool_task_claims_it(test_client, team):
    task = _admin_task(test_client, team["case"]["id"]).json()["task"]
    csrf = _as(test_client, "asha@example.com")
    started = test_client.patch(
        f"/api/v1/department/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": csrf},
    )
    assert started.status_code == 200
    assert started.json()["task"]["assigned_staff_id"] == team["ids"]["asha"]
    _as(test_client, "bela@example.com")
    assert test_client.get("/api/v1/department/tasks").json() == []


def test_admin_task_view_redacts_student_identity(test_client, team):
    csrf = _as(test_client, "coord@example.com")
    created = test_client.post(
        f"/api/v1/coordinator/cases/{team['case']['id']}/tasks",
        json={
            "department": "Counselling",
            "title": "Call Test Student",
            "instructions": "Email student@college.example.edu.in about a session.",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201

    _as(test_client, "main@example.com")
    listing = test_client.get("/api/v1/admin/tasks")
    assert listing.status_code == 200
    text = listing.text
    assert "student@college.example.edu.in" not in text
    assert "Test Student" not in text
    assert "[redacted]" in text


def test_admin_can_cancel_and_other_roles_cannot_use_admin_task_routes(
    test_client, team
):
    task = _admin_task(test_client, team["case"]["id"]).json()["task"]
    csrf = _as(test_client, "main@example.com")
    cancelled = test_client.patch(
        f"/api/v1/admin/tasks/{task['id']}",
        json={"action": "cancel"},
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["task"]["status"] == "cancelled"

    coord_csrf = _as(test_client, "coord@example.com")
    assert test_client.get("/api/v1/admin/tasks").status_code == 403
    assert test_client.post(
        f"/api/v1/admin/cases/{team['case']['id']}/tasks",
        json={
            "department": "Counselling",
            "title": "Sneaky task",
            "instructions": "Not allowed for coordinators.",
        },
        headers={"X-CSRF-Token": coord_csrf},
    ).status_code == 403


def test_department_staff_list_for_assignment(test_client, team):
    _as(test_client, "coord@example.com")
    listing = test_client.get("/api/v1/department-staff?department=counselling")
    assert listing.status_code == 200
    assert [s["name"] for s in listing.json()] == [
        "Asha Counsellor", "Bela Counsellor",
    ]
    assert test_client.get(
        "/api/v1/department-staff?department=Nowhere"
    ).status_code == 404
    _as(test_client, "asha@example.com")
    assert test_client.get(
        "/api/v1/department-staff?department=Counselling"
    ).status_code == 403


# ------------------------------------------------------------- messaging


def _send(test_client, email, **payload):
    csrf = _as(test_client, email)
    payload.setdefault("subject", "Quick question")
    payload.setdefault("body", "Can you help with this?")
    return test_client.post(
        "/api/v1/messages", json=payload, headers={"X-CSRF-Token": csrf}
    )


def test_staff_message_main_coordinator_and_read_state(test_client, team):
    sent = _send(test_client, "asha@example.com", recipient_type="main_coordinator")
    assert sent.status_code == 201
    assert sent.json()["recipient_count"] == 1

    csrf = _as(test_client, "main@example.com")
    assert test_client.get("/api/v1/messages/unread-count").json() == {"unread": 1}
    inbox = test_client.get("/api/v1/messages/inbox").json()
    assert len(inbox) == 1
    assert inbox[0]["sender_name"] == "Asha Counsellor"
    assert inbox[0]["sender_role_label"] == "Department Staff"
    assert inbox[0]["sender_department"] == "Counselling"
    assert inbox[0]["reply_target"] == {
        "recipient_type": "department",
        "recipient_department": "Counselling",
        "label": "Counselling",
    }
    assert test_client.patch(
        f"/api/v1/messages/{inbox[0]['id']}/read",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    assert test_client.get("/api/v1/messages/unread-count").json() == {"unread": 0}

    # Someone else cannot mark it read.
    other_csrf = _as(test_client, "bela@example.com")
    assert test_client.patch(
        f"/api/v1/messages/{inbox[0]['id']}/read",
        headers={"X-CSRF-Token": other_csrf},
    ).status_code == 404


def test_departments_can_message_each_other_but_not_themselves(
    test_client, team
):
    sent = _send(
        test_client, "chitra@example.com",
        recipient_type="department", recipient_department="counselling",
    )
    assert sent.status_code == 201
    # Fan-out: both Counselling staff receive their own copy.
    assert sent.json()["recipient_count"] == 2
    for email in ("asha@example.com", "bela@example.com"):
        _as(test_client, email)
        inbox = test_client.get("/api/v1/messages/inbox").json()
        assert len(inbox) == 1 and inbox[0]["sender_name"] == "Chitra Accounts"
        assert inbox[0]["audience_label"] == "Counselling"

    _as(test_client, "chitra@example.com")
    sent_view = test_client.get("/api/v1/messages/sent").json()
    assert len(sent_view) == 1
    assert sent_view[0]["recipient_count"] == 2
    assert sent_view[0]["read_count"] == 0

    own = _send(
        test_client, "chitra@example.com",
        recipient_type="department", recipient_department="Accounts",
    )
    assert own.status_code == 400
    missing = _send(
        test_client, "chitra@example.com",
        recipient_type="department", recipient_department="Nowhere",
    )
    assert missing.status_code == 400


def test_staff_can_only_message_coordinators_linked_to_their_department(
    test_client, team
):
    coordinator_id = team["ids"]["coordinator"]
    # Not linked yet: the case is not routed to Counselling.
    refused = _send(
        test_client, "asha@example.com",
        recipient_type="coordinator", recipient_user_id=coordinator_id,
    )
    assert refused.status_code == 403

    csrf = _as(test_client, "main@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{team['case']['id']}/department",
        json={"department": "Counselling"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    _as(test_client, "asha@example.com")
    recipients = test_client.get("/api/v1/messages/recipients").json()
    assert recipients["main_coordinator"] is True
    assert [c["id"] for c in recipients["coordinators"]] == [coordinator_id]
    assert recipients["departments"] == ["Accounts"]

    ok = _send(
        test_client, "asha@example.com",
        recipient_type="coordinator", recipient_user_id=coordinator_id,
    )
    assert ok.status_code == 201
    # The unrelated coordinator is still off limits.
    assert _send(
        test_client, "asha@example.com",
        recipient_type="coordinator",
        recipient_user_id=team["ids"]["other_coordinator"],
    ).status_code == 403


def test_main_coordinator_can_message_coordinators_and_departments(
    test_client, team
):
    to_coordinator = _send(
        test_client, "main@example.com",
        recipient_type="coordinator",
        recipient_user_id=team["ids"]["coordinator"],
    )
    assert to_coordinator.status_code == 201
    to_department = _send(
        test_client, "main@example.com",
        recipient_type="department", recipient_department="Accounts",
    )
    assert to_department.status_code == 201
    # The Main Coordinator is not a valid recipient for themselves.
    assert _send(
        test_client, "main@example.com", recipient_type="main_coordinator"
    ).status_code == 403

    _as(test_client, "coord@example.com")
    inbox = test_client.get("/api/v1/messages/inbox").json()
    assert inbox[0]["sender_role_label"] == "Main Coordinator"
    assert inbox[0]["reply_target"]["recipient_type"] == "main_coordinator"


def test_students_cannot_use_internal_messaging(test_client, team):
    csrf = _as(test_client, "student@college.example.edu.in")
    assert test_client.get("/api/v1/messages/inbox").status_code == 403
    assert test_client.get("/api/v1/messages/recipients").status_code == 403
    assert test_client.post(
        "/api/v1/messages",
        json={
            "recipient_type": "main_coordinator",
            "subject": "Hello",
            "body": "Hello there",
        },
        headers={"X-CSRF-Token": csrf},
    ).status_code == 403


def test_messages_require_login_and_csrf(test_client, team):
    assert test_client.get("/api/v1/messages/inbox").status_code == 401
    _as(test_client, "asha@example.com")
    assert test_client.post(
        "/api/v1/messages",
        json={
            "recipient_type": "main_coordinator",
            "subject": "Hello",
            "body": "Hello there",
        },
    ).status_code == 403


def test_message_validation(test_client, team):
    assert _send(
        test_client, "asha@example.com", recipient_type="coordinator"
    ).status_code == 422
    assert _send(
        test_client, "asha@example.com", recipient_type="department"
    ).status_code == 422
    assert _send(
        test_client, "asha@example.com",
        recipient_type="main_coordinator", body=" ",
    ).status_code == 422


def test_case_linked_messages_hide_identity_from_main_coordinator(
    test_client, team
):
    csrf = _as(test_client, "main@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{team['case']['id']}/department",
        json={"department": "Counselling"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    sent = _send(
        test_client, "asha@example.com",
        recipient_type="main_coordinator",
        case_id=team["case"]["id"],
        subject="Follow-up on Test Student",
        body="Please note student@college.example.edu.in asked for a call.",
    )
    assert sent.status_code == 201

    _as(test_client, "main@example.com")
    message = test_client.get("/api/v1/messages/inbox").json()[0]
    assert message["case_id"] == team["case"]["id"]
    assert "student@college.example.edu.in" not in message["body"]
    assert "Test Student" not in message["subject"]
    assert "[redacted]" in message["body"]
    assert message["case_title"]


def test_sender_cannot_reference_case_they_cannot_access(test_client, team):
    # Accounts staff have no access to a case that was never routed to them.
    response = _send(
        test_client, "chitra@example.com",
        recipient_type="main_coordinator", case_id=team["case"]["id"],
    )
    assert response.status_code == 404
