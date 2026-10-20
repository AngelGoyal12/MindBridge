"""Integration tests for the Coordinator -> Department task workflow."""

from datetime import timedelta

import pytest

from main import app, task_today
from test_auth import _create_test_user, _login_and_get_csrf


def _db():
    from auth.dependencies import get_db

    generator = app.dependency_overrides[get_db]()
    return generator, next(generator)


def _submit_case(test_client, student, **overrides):
    csrf = _login_and_get_csrf(test_client, student["email"], student["password"])
    payload = {
        "category": "academic",
        "title": "Exam stress and attendance",
        "description": "I am struggling to keep up with coursework this term.",
    }
    payload.update(overrides)
    response = test_client.post(
        "/api/v1/cases", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def workflow(test_client, test_student):
    """A case assigned to a coordinator, with staff in two departments."""
    case = _submit_case(test_client, test_student)
    coordinator_id = _create_test_user(
        "coordinator", "task-coordinator@example.com", name="Task Coordinator"
    )
    _create_test_user(
        "department_staff", "counselling@example.com",
        name="Counselling Staff", department="Counselling",
    )
    _create_test_user(
        "department_staff", "accounts@example.com",
        name="Accounts Staff", department="Accounts",
    )
    _create_test_user("admin", "task-admin@example.com")
    admin_csrf = _login_and_get_csrf(test_client, "task-admin@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200
    return {"case": case, "student": test_student, "coordinator_id": coordinator_id}


def _coordinator_login(test_client):
    return _login_and_get_csrf(test_client, "task-coordinator@example.com")


def _create_task(test_client, case_id, csrf, **overrides):
    payload = {
        "department": "Counselling",
        "title": "Schedule a counselling session",
        "instructions": "Offer the student a first session within a week.",
        "priority": "high",
    }
    payload.update(overrides)
    return test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/tasks",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )


def test_full_task_workflow_from_assignment_to_case_closure(
    test_client, workflow
):
    case_id = workflow["case"]["id"]
    coordinator_csrf = _coordinator_login(test_client)

    created = _create_task(test_client, case_id, coordinator_csrf, department="counselling")
    assert created.status_code == 201
    task = created.json()["task"]
    assert task["department"] == "Counselling"  # canonical casing
    assert task["status"] == "assigned"
    assert task["priority"] == "high"
    assert [e["to_status"] for e in task["events"]] == ["assigned"]

    # An open task blocks case closure.
    blocked = test_client.patch(
        f"/api/v1/coordinator/cases/{case_id}/status",
        json={"status": "closed", "closure_outcome": "Done."},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert blocked.status_code == 409
    assert "open" in blocked.json()["detail"]

    # Staff see the task and move it forward.
    staff_csrf = _login_and_get_csrf(test_client, "counselling@example.com")
    listing = test_client.get("/api/v1/department/tasks").json()
    assert [t["id"] for t in listing] == [task["id"]]
    assert listing[0]["case"]["id"] == case_id
    assert test_client.get("/api/v1/department/tasks/summary").json()["assigned"] == 1

    url = f"/api/v1/department/tasks/{task['id']}/status"
    assert test_client.patch(url, json={"status": "in_progress"}).status_code == 403  # CSRF
    started = test_client.patch(
        url, json={"status": "in_progress"}, headers={"X-CSRF-Token": staff_csrf}
    )
    assert started.status_code == 200
    assert started.json()["task"]["status"] == "in_progress"
    assert started.json()["task"]["started_at"] is not None

    # Completion needs a note, and cannot be repeated.
    assert test_client.patch(
        url, json={"status": "completed"}, headers={"X-CSRF-Token": staff_csrf}
    ).status_code == 422
    done = test_client.patch(
        url,
        json={"status": "completed", "note": "Session booked for Monday."},
        headers={"X-CSRF-Token": staff_csrf},
    )
    assert done.status_code == 200
    assert done.json()["task"]["completion_note"] == "Session booked for Monday."
    assert test_client.patch(
        url,
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": staff_csrf},
    ).status_code == 409

    # Coordinator reviews the result, then closes the case.
    coordinator_csrf = _coordinator_login(test_client)
    reviewed = test_client.get(f"/api/v1/coordinator/cases/{case_id}/tasks").json()
    assert reviewed[0]["status"] == "completed"
    assert [e["to_status"] for e in reviewed[0]["events"]] == [
        "assigned", "in_progress", "completed",
    ]
    assert reviewed[0]["events"][2]["actor_name"] == "Counselling Staff"
    closed = test_client.patch(
        f"/api/v1/coordinator/cases/{case_id}/status",
        json={"status": "closed", "closure_outcome": "Support delivered."},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert closed.status_code == 200

    # Student progress shows generic task milestones only.
    student = workflow["student"]
    _login_and_get_csrf(test_client, student["email"], student["password"])
    student_case = test_client.get(f"/api/v1/cases/{case_id}").json()
    task_updates = [u for u in student_case["progress_updates"] if u["type"] == "task"]
    assert [u["title"] for u in task_updates] == [
        "Support task assigned", "Support task completed",
    ]
    rendered = str(student_case)
    assert "Offer the student a first session" not in rendered
    assert "Session booked for Monday" not in rendered


def test_department_task_view_redacts_unconsented_identity(test_client, workflow):
    case_id = workflow["case"]["id"]
    csrf = _coordinator_login(test_client)
    created = _create_task(
        test_client,
        case_id,
        csrf,
        instructions="Please call Test Student at student@college.example.edu.in today.",
    )
    assert created.status_code == 201
    # The coordinator sees what they wrote.
    assert "Test Student" in created.json()["task"]["instructions"]

    _login_and_get_csrf(test_client, "counselling@example.com")
    task = test_client.get("/api/v1/department/tasks").json()[0]
    assert "Test Student" not in task["instructions"]
    assert "student@college.example.edu.in" not in task["instructions"]
    assert "[redacted]" in task["instructions"]
    assert "student_name" not in task["case"]
    assert "student_email" not in task["case"]


def test_task_access_is_scoped_by_role_department_and_coordinator(
    test_client, workflow
):
    case_id = workflow["case"]["id"]
    csrf = _coordinator_login(test_client)
    task_id = _create_task(test_client, case_id, csrf).json()["task"]["id"]

    # Another department cannot see or change it.
    other_csrf = _login_and_get_csrf(test_client, "accounts@example.com")
    assert test_client.get("/api/v1/department/tasks").json() == []
    assert test_client.get(f"/api/v1/department/tasks/{task_id}").status_code == 404
    assert test_client.patch(
        f"/api/v1/department/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": other_csrf},
    ).status_code == 404
    assert test_client.get("/api/v1/department/tasks/summary").json()["total"] == 0
    # Staff cannot use coordinator endpoints.
    assert test_client.get("/api/v1/coordinator/tasks").status_code == 403
    assert _create_task(test_client, case_id, other_csrf).status_code == 403

    # A coordinator who is not assigned to the case cannot see or create tasks.
    _create_test_user("coordinator", "other-coordinator@example.com")
    other_coordinator_csrf = _login_and_get_csrf(test_client, "other-coordinator@example.com")
    assert _create_task(test_client, case_id, other_coordinator_csrf).status_code == 404
    assert test_client.get(f"/api/v1/coordinator/cases/{case_id}/tasks").status_code == 404
    assert test_client.get("/api/v1/coordinator/tasks").json() == []
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{task_id}",
        json={"action": "cancel"},
        headers={"X-CSRF-Token": other_coordinator_csrf},
    ).status_code == 404

    # Students have no access to any task endpoint.
    student = workflow["student"]
    student_csrf = _login_and_get_csrf(test_client, student["email"], student["password"])
    assert test_client.get("/api/v1/department/tasks").status_code == 403
    assert test_client.get("/api/v1/coordinator/tasks").status_code == 403
    assert _create_task(test_client, case_id, student_csrf).status_code == 403

    # Unauthenticated callers are rejected.
    test_client.cookies.clear()
    assert test_client.get("/api/v1/department/tasks").status_code == 401
    assert test_client.get("/api/v1/coordinator/tasks").status_code == 401


def test_task_creation_validation(test_client, workflow):
    case_id = workflow["case"]["id"]
    csrf = _coordinator_login(test_client)

    # CSRF is mandatory.
    no_csrf = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/tasks",
        json={"department": "Counselling", "title": "Task title", "instructions": "Do the thing."},
    )
    assert no_csrf.status_code == 403
    assert _create_task(test_client, case_id, csrf, department="Unprovisioned").status_code == 400
    assert _create_task(test_client, case_id, csrf, priority="critical").status_code == 422
    assert _create_task(test_client, case_id, csrf, title="ab").status_code == 422
    assert _create_task(test_client, case_id, csrf, title="   ").status_code == 422
    yesterday = (task_today() - timedelta(days=1)).isoformat()
    assert _create_task(test_client, case_id, csrf, due_date=yesterday).status_code == 422
    today = task_today().isoformat()
    ok = _create_task(test_client, case_id, csrf, due_date=today)
    assert ok.status_code == 201
    assert ok.json()["task"]["is_overdue"] is False
    assert test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/tasks",
        json={"department": "Counselling", "title": "Task title",
              "instructions": "Do the thing.", "status": "completed"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 422  # extra fields are rejected
    assert _create_task(test_client, 99999, csrf).status_code == 404


def test_coordinator_can_cancel_and_reopen_tasks(test_client, workflow):
    case_id = workflow["case"]["id"]
    csrf = _coordinator_login(test_client)
    cancelled_id = _create_task(test_client, case_id, csrf).json()["task"]["id"]
    reopened_id = _create_task(
        test_client, case_id, csrf, title="Second task for reopening"
    ).json()["task"]["id"]

    cancel = test_client.patch(
        f"/api/v1/coordinator/tasks/{cancelled_id}",
        json={"action": "cancel", "note": "No longer needed."},
        headers={"X-CSRF-Token": csrf},
    )
    assert cancel.status_code == 200
    assert cancel.json()["task"]["status"] == "cancelled"
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{cancelled_id}",
        json={"action": "cancel"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 409
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{reopened_id}",
        json={"action": "reopen", "note": "Not completed yet."},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 409  # only completed tasks can be reopened

    # Staff cannot act on a cancelled task.
    staff_csrf = _login_and_get_csrf(test_client, "counselling@example.com")
    assert test_client.patch(
        f"/api/v1/department/tasks/{cancelled_id}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": staff_csrf},
    ).status_code == 409

    # Complete the second task, then reopen it with a reason.
    assert test_client.patch(
        f"/api/v1/department/tasks/{reopened_id}/status",
        json={"status": "completed", "note": "Finished early."},
        headers={"X-CSRF-Token": staff_csrf},
    ).status_code == 200
    csrf = _coordinator_login(test_client)
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{reopened_id}",
        json={"action": "reopen"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 422  # reason required
    reopened = test_client.patch(
        f"/api/v1/coordinator/tasks/{reopened_id}",
        json={"action": "reopen", "note": "Please include a follow-up date."},
        headers={"X-CSRF-Token": csrf},
    )
    assert reopened.status_code == 200
    body = reopened.json()["task"]
    assert body["status"] == "assigned"
    assert body["completion_note"] is None
    assert body["completed_at"] is None

    # With the cancelled task ignored, the reopened one still blocks closure.
    assert test_client.patch(
        f"/api/v1/coordinator/cases/{case_id}/status",
        json={"status": "closed", "closure_outcome": "Done."},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 409
    assert test_client.patch(
        f"/api/v1/coordinator/tasks/{reopened_id}",
        json={"action": "cancel"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    assert test_client.patch(
        f"/api/v1/coordinator/cases/{case_id}/status",
        json={"status": "closed", "closure_outcome": "Done."},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    # No new tasks on a closed case.
    assert _create_task(test_client, case_id, csrf).status_code == 409


def test_staff_may_complete_directly_and_summary_counts_overdue(
    test_client, workflow
):
    import models

    case_id = workflow["case"]["id"]
    csrf = _coordinator_login(test_client)
    first = _create_task(test_client, case_id, csrf).json()["task"]["id"]
    second = _create_task(test_client, case_id, csrf, title="Another task").json()["task"]["id"]
    _create_task(test_client, case_id, csrf, department="Accounts", title="Accounts task")

    generator, db = _db()
    try:
        task = db.query(models.DepartmentTask).filter_by(id=second).one()
        task.due_date = task_today() - timedelta(days=2)
        db.commit()
    finally:
        generator.close()

    staff_csrf = _login_and_get_csrf(test_client, "counselling@example.com")
    summary = test_client.get("/api/v1/department/tasks/summary").json()
    assert summary["total"] == 2  # Accounts task is not counted
    assert summary["assigned"] == 2
    assert summary["overdue"] == 1
    overdue = [t for t in test_client.get("/api/v1/department/tasks").json() if t["is_overdue"]]
    assert [t["id"] for t in overdue] == [second]

    assert test_client.patch(
        f"/api/v1/department/tasks/{first}/status",
        json={"status": "completed", "note": "Handled in one call."},
        headers={"X-CSRF-Token": staff_csrf},
    ).status_code == 200
    summary = test_client.get("/api/v1/department/tasks/summary").json()
    assert summary["completed"] == 1 and summary["assigned"] == 1
    filtered = test_client.get("/api/v1/department/tasks?status=completed").json()
    assert [t["id"] for t in filtered] == [first]
    assert test_client.get("/api/v1/department/tasks?status=bogus").status_code == 422

    # Coordinator overview lists tasks across departments for their cases.
    _coordinator_login(test_client)
    everything = test_client.get("/api/v1/coordinator/tasks").json()
    assert len(everything) == 3
    assert {t["department"] for t in everything} == {"Counselling", "Accounts"}
