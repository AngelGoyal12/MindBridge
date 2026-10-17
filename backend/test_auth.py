
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from main import app
from auth.security import hash_password, verify_password

# ============================================================
# Password security tests
# ============================================================

def test_password_hash_is_not_plain_text():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)


def test_wrong_password_is_rejected():
    hashed = hash_password("CorrectPassword123!")

    assert not verify_password("WrongPassword123!", hashed)


def test_same_password_gets_different_hashes():
    password = "TestPassword123!"

    hash_one = hash_password(password)
    hash_two = hash_password(password)

    assert hash_one != hash_two
    assert verify_password(password, hash_one)
    assert verify_password(password, hash_two)


# ============================================================
# Authentication access tests
# ============================================================

def test_me_requires_login(test_client):
    response = test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_case_list_requires_login(test_client):
    response = test_client.get("/api/v1/cases")
    assert response.status_code == 401


def test_case_creation_requires_login(test_client):
    response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Test case",
            "description": "This is a test case description.",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_user(test_client):
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown-user@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_me_and_logout(test_client, test_student):
    # Login with valid credentials
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200
    assert "mindbridge_session" in login_response.cookies
    cookie_header = login_response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header

    csrf_token = login_response.json()["csrf_token"]

    # Verify authenticated user
    me_response = test_client.get("/api/v1/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == test_student["email"]

    # Logout with CSRF token
    session_token = login_response.cookies.get("mindbridge_session")
    logout_response = test_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert logout_response.status_code == 200

    # Session must no longer work
    me_after_logout = test_client.get("/api/v1/auth/me")
    assert me_after_logout.status_code == 401

    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        session = (
            db.query(models.UserSession)
            .filter(
                models.UserSession.token_hash
                == hashlib.sha256(session_token.encode()).hexdigest()
            )
            .first()
        )
        assert session is not None
        assert session.revoked_at is not None
    finally:
        db.close()


def test_expired_session_is_rejected(test_client, test_student):
    from auth.dependencies import get_db
    import models

    _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        session = (
            db.query(models.UserSession)
            .join(models.User, models.UserSession.user_id == models.User.id)
            .filter(models.User.email == test_student["email"])
            .first()
        )
        assert session is not None
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    assert test_client.get("/api/v1/auth/me").status_code == 401


def test_login_rejects_wrong_password(test_client, test_student):
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_student["email"],
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_throttles_repeated_bad_passwords(test_client, test_student):
    for _ in range(5):
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_student["email"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    throttled = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )
    assert throttled.status_code == 429
    assert int(throttled.headers["Retry-After"]) > 0


def test_account_login_limit_applies_across_source_addresses():
    from main import (
        _login_rate_limit_retry_after,
        _record_failed_login,
        reset_login_attempts,
    )

    reset_login_attempts()
    email = "distributed-attempts@example.com"
    for index in range(5):
        _record_failed_login(f"client-{index}", email)
    assert _login_rate_limit_retry_after("another-client", email) is not None
    reset_login_attempts()


def test_production_requires_secure_session_cookies():
    from auth.sessions import resolve_cookie_secure

    assert not resolve_cookie_secure("development", "false")
    assert resolve_cookie_secure("production", "true")
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE=true"):
        resolve_cookie_secure("production", "false")


def test_api_responses_include_security_headers_and_trusted_cors(test_client):
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown-user@example.com",
            "password": "WrongPassword123!",
        },
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'; object-src 'none'"
    )
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "strict-transport-security" not in response.headers


def test_security_headers_allow_fastapi_api_documentation(test_client):
    response = test_client.get("/docs")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    policy = response.headers["content-security-policy"]
    assert "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in policy
    assert "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in policy
    assert "frame-ancestors 'none'" in policy


def test_production_security_headers_require_secure_cookie_configuration(
    test_client,
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    import auth.sessions
    monkeypatch.setattr(auth.sessions, "COOKIE_SECURE", True)

    response = test_client.get("/")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_production_session_cookie_is_secure(test_client, test_student, monkeypatch):
    import auth.sessions

    monkeypatch.setattr(auth.sessions, "COOKIE_SECURE", True)
    response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert response.status_code == 200
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "secure" in cookie_header
    assert "samesite=lax" in cookie_header


# ============================================================
# Student case privacy tests
# ============================================================

def test_student_cannot_access_another_students_case(
    test_client,
    test_student,
):
    # Login as Student A
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    # Create Student A's case
    create_response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Student A case",
            "description": "A private case for Student A.",
        },
        headers={"X-CSRF-Token": csrf_token},
    )

    assert create_response.status_code == 201
    case_id = create_response.json()["id"]

    # Insert Student B and their case into the isolated test DB
    from auth.dependencies import get_db
    import models

    override_get_db = app.dependency_overrides[get_db]
    db_generator = override_get_db()
    db = next(db_generator)

    try:
        student_b = models.User(
            name="Student B",
            email="student-b@example.com",
            password_hash=hash_password("StudentBPassword123!"),
            role="student",
        )

        db.add(student_b)
        db.commit()
        db.refresh(student_b)

        case_b = models.Case(
            student_id=student_b.id,
            category="academic",
            title="Student B private case",
            description="A private case for Student B.",
            status="submitted",
        )

        db.add(case_b)
        db.commit()
        db.refresh(case_b)

        case_b_id = case_b.id

    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

    # Student A must not access Student B's case
    response = test_client.get(
        f"/api/v1/cases/{case_b_id}"
    )

    assert response.status_code == 404

    # Student A can access their own case
    own_response = test_client.get(
        f"/api/v1/cases/{case_id}"
    )

    assert own_response.status_code == 200


# ============================================================
# CSRF protection tests
# ============================================================

def test_case_creation_rejects_missing_csrf_token(
    test_client,
    test_student,
):
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200

    response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "CSRF test",
            "description": "Testing missing CSRF token.",
        },
    )

    assert response.status_code == 403


def test_logout_rejects_missing_csrf_token(
    test_client,
    test_student,
):
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200

    response = test_client.post("/api/v1/auth/logout")

    assert response.status_code == 403


def test_csrf_refresh_requires_a_trusted_origin(
    test_client,
    test_student,
):
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )
    assert login_response.status_code == 200

    untrusted = test_client.post(
        "/api/v1/auth/csrf",
        headers={"Origin": "https://untrusted.example"},
    )
    assert untrusted.status_code == 403

    trusted = test_client.post(
        "/api/v1/auth/csrf",
        headers={"Origin": "http://localhost:5173"},
    )
    assert trusted.status_code == 200


# ============================================================
# Student authorization tests
# ============================================================

def test_student_cannot_update_case(
    test_client,
    test_student,
):
    # Login as a student
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    # Try to update a case as a student
    response = test_client.patch(
        "/api/v1/cases/1",
        json={"status": "resolved"},
        headers={"X-CSRF-Token": csrf_token},
    )

    # Students must not be allowed to update cases
    assert response.status_code == 403


def test_case_creation_ignores_client_supplied_student_id(
    test_client,
    test_student,
):
    # Login as Student A
    login_response = test_client.post(
        "/api/v1/auth/login",
        json=test_student,
    )

    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    # Attempt to create a case for another student
    response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Ownership security test",
            "description": "Testing that the client cannot set ownership.",
            "student_id": 999999,
            "role": "admin",
            "department": "Trusted Department",
            "assigned_coordinator_id": 999999,
        },
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 201

    # Verify ownership through the API's case listing
    cases_response = test_client.get("/api/v1/cases")

    assert cases_response.status_code == 200

    created_case_id = response.json()["id"]
    created_case = next(
        (
            case
            for case in cases_response.json()
            if case["id"] == created_case_id
        ),
        None,
    )

    assert created_case is not None
    assert created_case["title"] == "Ownership security test"


def test_notifications_are_limited_to_the_authenticated_student(
    test_client,
    test_student,
):
    student_a_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case_a = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Student A notification",
            "description": "Only Student A should receive this update.",
        },
        headers={"X-CSRF-Token": student_a_csrf},
    ).json()

    _create_test_user("student", "student-b-notifications@example.com")
    student_b_csrf = _login_and_get_csrf(
        test_client,
        "student-b-notifications@example.com",
    )
    test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Student B notification",
            "description": "Only Student B should receive this update.",
        },
        headers={"X-CSRF-Token": student_b_csrf},
    )

    _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    notifications = test_client.get("/api/v1/notifications")
    assert notifications.status_code == 200
    assert [item["case_id"] for item in notifications.json()] == [case_a["id"]]


# ============================================================
# Test helper functions
# ============================================================

def _create_test_user(
    role: str,
    email: str,
    name: str = "Test User",
    password: str = "TestPassword123!",
    department: str | None = None,
):
    import models
    from auth.dependencies import get_db

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        user = models.User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            department=department,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db_generator.close()


def _login_and_get_csrf(
    test_client,
    email,
    password="TestPassword123!",
):
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200
    return response.json()["csrf_token"]


# ============================================================
# Registration role security tests
# ============================================================

@pytest.mark.parametrize(
    "role",
    ["admin", "coordinator", "department_staff"],
)
def test_public_registration_cannot_create_privileged_roles(
    test_client,
    monkeypatch,
    role,
):
    import main

    monkeypatch.setattr(main, "send_verification_email", lambda *_args: None)
    email = f"attempted-{role}@college.example.edu.in"
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Attempted Admin",
            "email": email,
            "phone": "9876543210",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "role": role,
            "department": "Untrusted Department",
        },
    )

    assert response.status_code == 202
    assert "user" not in response.json()
    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.query(models.User).filter(
            models.User.email == email
        ).first() is None
    finally:
        db.close()


@pytest.mark.parametrize(
    ("role", "department"),
    [
        ("admin", None),
        ("coordinator", None),
    ],
)
def test_provisioning_accepts_admin_and_coordinator_roles(role, department):
    from provision_user import _validate_provisioning_fields

    _validate_provisioning_fields(
        "Provisioned Account",
        role,
        department,
        "StrongProvisioning123!",
    )


def test_provisioning_rejects_invalid_privileged_account_fields():
    from provision_user import _validate_provisioning_fields

    with pytest.raises(ValueError, match="department staff accounts"):
        _validate_provisioning_fields(
            "Staff Account",
            "department_staff",
            None,
            "StrongProvisioning123!",
        )
    with pytest.raises(ValueError, match="only valid for department staff"):
        _validate_provisioning_fields(
            "Admin Account",
            "admin",
            "CSE",
            "StrongProvisioning123!",
        )
    with pytest.raises(ValueError, match="Password must include"):
        _validate_provisioning_fields(
            "Coordinator Account",
            "coordinator",
            None,
            "weakpassword",
        )


@pytest.mark.parametrize("role", ["admin", "coordinator"])
def test_provisioning_command_creates_hashed_admin_and_coordinator(
    monkeypatch,
    capsys,
    role,
):
    import sys
    from unittest.mock import MagicMock

    import provision_user

    db = MagicMock()
    db.__enter__.return_value = db
    db.query.return_value.filter.return_value.first.return_value = None
    monkeypatch.setattr(provision_user, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "provision_user.py",
            "--name",
            "Provisioned Account",
            "--email",
            f"{role}@EXAMPLE.COM",
            "--role",
            role,
        ],
    )
    password = "StrongProvisioning123!"
    prompts = iter((password, password))
    monkeypatch.setattr(provision_user, "getpass", lambda _prompt: next(prompts))

    provision_user.main()

    provisioned_user = db.add.call_args.args[0]
    assert provisioned_user.role == role
    assert provisioned_user.email == f"{role}@example.com"
    assert provisioned_user.department is None
    assert provisioned_user.password_hash != password
    assert verify_password(password, provisioned_user.password_hash)
    assert password not in capsys.readouterr().out
    db.commit.assert_called_once()


def test_staff_provisioning_uses_existing_canonical_department(
    monkeypatch,
):
    import sys
    from unittest.mock import MagicMock

    import provision_user

    db = MagicMock()
    db.__enter__.return_value = db
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        ("Counselling",),
    ]
    monkeypatch.setattr(provision_user, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "provision_user.py",
            "--name",
            "Provisioned Staff",
            "--email",
            "staff@example.edu",
            "--role",
            "department_staff",
            "--department",
            " cOUNSELLING ",
        ],
    )
    password = "StrongProvisioning123!"
    prompts = iter((password, password))
    monkeypatch.setattr(provision_user, "getpass", lambda _prompt: next(prompts))

    provision_user.main()

    assert db.add.call_args.args[0].department == "Counselling"


def _start_pending_registration(
    test_client,
    monkeypatch,
    email="new.student@college.example.edu.in",
):
    import main

    issued_codes = []

    def record_email(recipient, otp, expiration_seconds):
        issued_codes.append((recipient, otp, expiration_seconds))

    monkeypatch.setattr(main, "send_verification_email", record_email)
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Student",
            "email": email,
            "phone": "+91 98765 43210",
            "password": "NewStudentPassword123!",
            "confirm_password": "NewStudentPassword123!",
            "role": "admin",
            "department": "Untrusted",
        },
    )
    return response, issued_codes


def test_registration_requires_configured_college_email_domain(test_client):
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Personal Email",
            "email": "person@gmail.com",
            "phone": "9876543210",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
        },
    )
    assert response.status_code == 422


def test_registration_accepts_configured_edu_in_domains(
    test_client,
    monkeypatch,
):
    import main

    monkeypatch.setenv(
        "COLLEGE_EMAIL_DOMAINS",
        "college.example.edu.in,another-college.edu.in",
    )
    monkeypatch.setattr(main, "send_verification_email", lambda *_args: None)
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Another College Student",
            "email": "student@another-college.edu.in",
            "phone": "9876543210",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
        },
    )
    assert response.status_code == 202
    assert response.json()["resend_cooldown_seconds"] == 60


@pytest.mark.parametrize(
    "password",
    [
        "Short1!Aa",
        "longpassword123!",
        "LONGPASSWORD123!",
        "LongPassword!!",
        "LongPassword123",
    ],
)
def test_registration_rejects_weak_passwords(test_client, password):
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Weak Password",
            "email": "weak.password@college.example.edu.in",
            "phone": "9876543210",
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 422
    assert password not in response.text


def test_registration_rejects_password_mismatch(test_client):
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Mismatched Password",
            "email": "mismatch@college.example.edu.in",
            "phone": "9876543210",
            "password": "ValidPassword123!",
            "confirm_password": "AnotherPassword123!",
        },
    )
    assert response.status_code == 422
    assert "ValidPassword123!" not in response.text


def test_validation_errors_do_not_echo_one_time_codes(test_client):
    response = test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": "student@college.example.edu.in", "otp": "12345"},
    )
    assert response.status_code == 422
    assert '"input":"12345"' not in response.text


@pytest.mark.parametrize(
    "email",
    [
        "student@gmail.com",
        "student@yahoo.com",
        "student@company.edu",
        "student@edu.in",
        "student@other-college.edu.in",
    ],
)
def test_registration_rejects_non_edu_in_addresses(test_client, email):
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Non College Address",
            "email": email,
            "phone": "9876543210",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "phone",
    ["1234567890", "987654321", "+91 12345 67890", "98765abc10"],
)
def test_registration_rejects_invalid_indian_mobile_numbers(test_client, phone):
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Invalid Phone",
            "email": "invalid.phone@college.example.edu.in",
            "phone": phone,
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
        },
    )
    assert response.status_code == 422


def test_registration_duplicate_account_is_generic_and_no_resend(
    test_client,
    test_student,
    monkeypatch,
):
    import main

    deliveries = []
    monkeypatch.setattr(
        main,
        "send_verification_email",
        lambda *args: deliveries.append(args),
    )
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate Student",
            "email": test_student["email"],
            "phone": "9876543210",
            "password": "NewStudentPassword123!",
            "confirm_password": "NewStudentPassword123!",
        },
    )
    assert response.status_code == 202
    assert response.json()["resend_cooldown_seconds"] == 60
    assert "user" not in response.json()
    assert deliveries == []


def test_otp_delivery_failure_does_not_activate_account(
    test_client,
    monkeypatch,
):
    import main

    def fail_delivery(*_args):
        raise smtplib.SMTPException("test delivery failure")

    import smtplib
    monkeypatch.setattr(main, "send_verification_email", fail_delivery)
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Student",
            "email": "delivery.failure@college.example.edu.in",
            "phone": "9876543210",
            "password": "NewStudentPassword123!",
            "confirm_password": "NewStudentPassword123!",
        },
    )
    assert response.status_code == 503
    assert "otp" not in response.text.lower()
    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.query(models.PendingEmailVerification).filter_by(
            email="delivery.failure@college.example.edu.in"
        ).first() is None
    finally:
        db.close()
    assert test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "delivery.failure@college.example.edu.in",
            "password": "NewStudentPassword123!",
        },
    ).status_code == 401


def test_missing_smtp_configuration_does_not_create_pending_registration(
    test_client,
    monkeypatch,
):
    from auth.dependencies import get_db
    import models

    monkeypatch.delenv("SMTP_HOST")
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "No SMTP",
            "email": "no.smtp@college.example.edu.in",
            "phone": "9876543210",
            "password": "NewStudentPassword123!",
            "confirm_password": "NewStudentPassword123!",
        },
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.query(models.PendingEmailVerification).filter_by(
            email="no.smtp@college.example.edu.in"
        ).first() is None
    finally:
        db.close()


def test_resend_delivery_failure_restores_previous_code_and_limits(
    test_client,
    monkeypatch,
):
    import smtplib

    from auth.dependencies import get_db
    import models

    response, issued_codes = _start_pending_registration(
        test_client,
        monkeypatch,
        "resend.failure@college.example.edu.in",
    )
    assert response.status_code == 202
    email, original_otp, _ = issued_codes[0]

    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        pending.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        original_last_sent_at = pending.last_sent_at
        original_otp_hash = pending.otp_hash
        db.commit()
    finally:
        db.close()

    import main

    def fail_delivery(*_args):
        raise smtplib.SMTPException("test resend failure")

    monkeypatch.setattr(main, "send_verification_email", fail_delivery)
    resent = test_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )
    assert resent.status_code == 503

    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        assert pending.otp_hash == original_otp_hash
        assert pending.resend_count == 0
        assert (
            pending.last_sent_at.replace(tzinfo=timezone.utc)
            == original_last_sent_at
        )
    finally:
        db.close()

    assert test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": original_otp},
    ).status_code == 200


def test_email_otp_verifies_once_and_only_then_allows_login(
    test_client,
    monkeypatch,
):
    response, issued_codes = _start_pending_registration(
        test_client,
        monkeypatch,
        "verified.student@COLLEGE.EXAMPLE.EDU.IN",
    )
    assert response.status_code == 202
    assert len(issued_codes) == 1
    email, otp, expiry = issued_codes[0]
    assert email == "verified.student@college.example.edu.in"
    assert expiry == 300
    assert otp not in response.text
    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        assert pending.otp_hash != otp
        assert pending.password_hash != "NewStudentPassword123!"
        assert pending.phone == "+919876543210"
    finally:
        db.close()

    assert test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "NewStudentPassword123!"},
    ).status_code == 401

    invalid = test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": "000000" if otp != "000000" else "000001"},
    )
    assert invalid.status_code == 400

    verified = test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": otp},
    )
    assert verified.status_code == 200
    profile = test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "NewStudentPassword123!"},
    )
    assert profile.status_code == 200
    assert profile.json()["user"]["phone"] == "+919876543210"
    assert profile.json()["user"]["role"] == "student"
    assert profile.json()["user"]["department"] is None
    assert test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "NewStudentPassword123!"},
    ).status_code == 200

    replay = test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": otp},
    )
    assert replay.status_code == 400


def test_otp_expires_and_resend_supersedes_previous_code(
    test_client,
    monkeypatch,
):
    from auth.dependencies import get_db
    import models

    response, issued_codes = _start_pending_registration(
        test_client,
        monkeypatch,
        "resend.student@college.example.edu.in",
    )
    assert response.status_code == 202
    old_code = issued_codes[0][1]
    email = issued_codes[0][0]

    cooldown = test_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )
    assert cooldown.status_code == 202
    assert len(issued_codes) == 1

    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        pending.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        db.commit()
    finally:
        db.close()

    resent = test_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )
    assert resent.status_code == 202
    assert len(issued_codes) == 2
    new_code = issued_codes[1][1]
    assert old_code != new_code
    assert test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": old_code},
    ).status_code == 400

    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        pending.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    expired = test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": new_code},
    )
    assert expired.status_code == 400
    assert "expired" in expired.json()["detail"].lower()


def test_otp_verification_attempt_limit(test_client, monkeypatch):
    response, issued_codes = _start_pending_registration(
        test_client,
        monkeypatch,
        "attempt.limit@college.example.edu.in",
    )
    assert response.status_code == 202
    email, otp, _ = issued_codes[0]
    bad_code = "000000" if otp != "000000" else "000001"
    for _ in range(4):
        assert test_client.post(
            "/api/v1/auth/verify-email",
            json={"email": email, "otp": bad_code},
        ).status_code == 400
    assert test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": bad_code},
    ).status_code == 429
    assert test_client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "otp": otp},
    ).status_code == 429


def test_otp_resend_limit_is_enforced(test_client, monkeypatch):
    from auth.dependencies import get_db
    import models

    response, issued_codes = _start_pending_registration(
        test_client,
        monkeypatch,
        "resend.limit@college.example.edu.in",
    )
    assert response.status_code == 202
    email = issued_codes[0][0]
    db = next(app.dependency_overrides[get_db]())
    try:
        pending = db.query(models.PendingEmailVerification).filter_by(
            email=email
        ).one()
        pending.resend_count = 5
        pending.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        db.commit()
    finally:
        db.close()

    response = test_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )
    assert response.status_code == 202
    assert len(issued_codes) == 1


def test_each_provisioned_role_can_log_in(test_client):
    accounts = [
        ("student", "login-student@example.com", None),
        ("coordinator", "login-coordinator@example.com", None),
        ("admin", "login-admin@example.com", None),
        (
            "department_staff",
            "login-department@example.com",
            "Counselling",
        ),
    ]

    for role, email, department in accounts:
        _create_test_user(
            role=role,
            email=email,
            department=department,
        )
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200
        assert response.json()["user"]["role"] == role
        current_user = test_client.get("/api/v1/auth/me")
        assert current_user.status_code == 200
        assert current_user.json()["role"] == role


def test_admin_and_coordinator_permissions_are_separate(test_client):
    _create_test_user("admin", "role-admin@example.com")
    _create_test_user("coordinator", "role-coordinator@example.com")

    admin_csrf = _login_and_get_csrf(test_client, "role-admin@example.com")
    assert test_client.get("/api/v1/admin/cases").status_code == 200
    assert test_client.get("/api/v1/admin/coordinators").status_code == 200
    assert test_client.get("/api/v1/coordinator/cases").status_code == 403
    assert test_client.get("/api/v1/department/cases").status_code == 403
    assert test_client.post(
        "/api/v1/coordinator/cases/1/identity-disclosure",
        json={"purpose": "Support", "scope": "Follow-up"},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 403
    assert test_client.post(
        "/api/v1/cases/1/consent",
        json={
            "purpose": "Support",
            "recipient": "role-coordinator@example.com",
            "scope": "Follow-up",
        },
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 403

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "role-coordinator@example.com",
    )
    assert test_client.get("/api/v1/coordinator/cases").status_code == 200
    assert test_client.get("/api/v1/admin/cases").status_code == 403
    assert test_client.get("/api/v1/admin/coordinators").status_code == 403
    assert test_client.get("/api/v1/department/cases").status_code == 403
    assert test_client.patch(
        "/api/v1/cases/1/assign",
        json={"coordinator_id": 1},
        headers={"X-CSRF-Token": coordinator_csrf},
    ).status_code == 403
    assert test_client.patch(
        "/api/v1/cases/1/department",
        json={"department": "CSE"},
        headers={"X-CSRF-Token": coordinator_csrf},
    ).status_code == 404
    assert test_client.get("/api/v1/departments").status_code == 200


def test_coordinator_case_status_update_requires_valid_csrf(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Coordinator CSRF case",
            "description": "This case checks coordinator CSRF enforcement.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    coordinator_id = _create_test_user(
        "coordinator",
        "coordinator-csrf@example.com",
    )
    _create_test_user("admin", "admin-csrf-assign@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "admin-csrf-assign@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "coordinator-csrf@example.com",
    )
    endpoint = f"/api/v1/coordinator/cases/{case['id']}/status"
    update = {"status": "in_progress"}
    assert test_client.patch(endpoint, json=update).status_code == 403
    assert test_client.patch(
        endpoint,
        json=update,
        headers={"X-CSRF-Token": "invalid"},
    ).status_code == 403
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case['id']}"
    ).json()["status"] == "submitted"
    assert test_client.patch(
        endpoint,
        json=update,
        headers={"X-CSRF-Token": coordinator_csrf},
    ).status_code == 200


def test_department_staff_without_trusted_department_cannot_log_in(
    test_client,
):
    _create_test_user(
        role="department_staff",
        email="unassigned-staff@example.com",
    )

    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unassigned-staff@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 403
    assert "mindbridge_session" not in response.cookies


def test_unknown_database_role_cannot_create_a_session(test_client):
    _create_test_user(
        role="superuser",
        email="unknown-role@example.com",
    )
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown-role@example.com",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 403
    assert "mindbridge_session" not in response.cookies


# ============================================================
# Case assignment authorization tests
# ============================================================

def test_student_cannot_assign_case(test_client, test_student):
    csrf_token = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )

    response = test_client.patch(
        "/api/v1/cases/1/assign",
        json={"coordinator_id": 999},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 403


def test_coordinator_cannot_assign_case(test_client):
    _create_test_user(
        role="coordinator",
        email="coordinator-assign@example.com",
    )

    csrf_token = _login_and_get_csrf(
        test_client,
        "coordinator-assign@example.com",
    )

    response = test_client.patch(
        "/api/v1/cases/1/assign",
        json={"coordinator_id": 999},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 403


def test_admin_can_assign_case_to_coordinator(
    test_client,
    test_student,
    monkeypatch,
):
    import main

    sent_messages = []
    monkeypatch.setattr(
        main,
        "send_coordinator_assignment_email",
        lambda *args: sent_messages.append(args),
    )
    # Create a case as a student
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )

    case_response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Assignment test case",
            "description": "A case for testing coordinator assignment.",
        },
        headers={"X-CSRF-Token": student_csrf},
    )

    assert case_response.status_code == 201
    case_id = case_response.json()["id"]

    # Create the admin and coordinator
    _create_test_user(
        role="admin",
        email="admin-assign@example.com",
    )

    coordinator_id = _create_test_user(
        role="coordinator",
        email="coordinator-target@example.com",
    )

    # Log in as admin and assign the case
    admin_csrf = _login_and_get_csrf(
        test_client,
        "admin-assign@example.com",
    )

    response = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_email": "COORDINATOR-TARGET@example.com"},
        headers={"X-CSRF-Token": admin_csrf},
    )

    assert response.status_code == 200
    assert response.json()["case"]["id"] == case_id
    assert response.json()["assignment_status"] == "assigned"
    assert response.json()["coordinator_email"] == "coordinator-target@example.com"
    assert sent_messages == [
        ("coordinator-target@example.com", case_id, "academic")
    ]

    # Log in as the assigned coordinator
    _login_and_get_csrf(
        test_client,
        "coordinator-target@example.com",
    )

    assigned_cases = test_client.get(
        "/api/v1/coordinator/cases",
    )

    assert assigned_cases.status_code == 200
    assert any(
        case["id"] == case_id
        for case in assigned_cases.json()
    )


def test_admin_assignment_rejects_invalid_or_non_coordinator_email(
    test_client,
    test_student,
):
    _create_test_user("admin", "email-assignment-admin@example.com")
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case_id = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Email validation assignment",
            "description": "The administrator must assign the correct account.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()["id"]
    admin_csrf = _login_and_get_csrf(
        test_client,
        "email-assignment-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_email": "nobody@example.edu"},
    ).status_code == 403

    invalid_email = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_email": "not-an-email"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert invalid_email.status_code == 422
    student_email = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_email": test_student["email"]},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert student_email.status_code == 400
    assert test_client.get("/api/v1/admin/cases").json()[0][
        "assigned_coordinator_id"
    ] is None


def test_new_coordinator_invitation_is_hashed_single_use_and_assigns_case(
    test_client,
    test_student,
    monkeypatch,
):
    import main
    from auth.dependencies import get_db
    import models

    sent_invitations = []
    monkeypatch.setattr(
        main,
        "send_coordinator_invitation_email",
        lambda *args: sent_invitations.append(args),
    )
    _create_test_user("admin", "invite-admin@example.com")
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Student private title",
            "description": "Student protected report details.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    admin_csrf = _login_and_get_csrf(test_client, "invite-admin@example.com")

    response = test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_email": "new.coordinator@example.edu"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 200
    assert response.json()["assignment_status"] == "invitation_sent"
    assert "token" not in response.json()
    assert "Student private title" not in response.text
    assert "Student protected report details." not in response.text
    assert len(sent_invitations) == 1
    email, token, case_id, category = sent_invitations[0]
    assert (email, case_id, category) == (
        "new.coordinator@example.edu",
        case["id"],
        "academic",
    )

    db = next(app.dependency_overrides[get_db]())
    try:
        invitation = db.query(models.CoordinatorInvitation).filter_by(
            email=email
        ).one()
        assert invitation.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert invitation.token_hash != token
        assert invitation.accepted_at is None
        assert db.query(models.Case).filter_by(id=case_id).one().assigned_coordinator_id is None
    finally:
        db.close()

    role_escalation = test_client.post(
        "/api/v1/coordinator-invitations/accept",
        json={
            "token": token,
            "name": "Invited Coordinator",
            "password": "InvitedCoordinator123!",
            "confirm_password": "InvitedCoordinator123!",
            "role": "admin",
        },
    )
    assert role_escalation.status_code == 422
    assert token not in role_escalation.text

    accepted = test_client.post(
        "/api/v1/coordinator-invitations/accept",
        json={
            "token": token,
            "name": "Invited Coordinator",
            "password": "InvitedCoordinator123!",
            "confirm_password": "InvitedCoordinator123!",
        },
    )
    assert accepted.status_code == 201
    assert accepted.json()["dashboard_url"].endswith("/dashboard/coordinator")
    assert test_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "InvitedCoordinator123!",
        },
    ).json()["user"]["role"] == "coordinator"
    assigned_cases = test_client.get("/api/v1/coordinator/cases")
    assert [item["id"] for item in assigned_cases.json()] == [case_id]
    assert "Student private title" not in assigned_cases.text
    assert "Student protected report details." not in assigned_cases.text

    replay = test_client.post(
        "/api/v1/coordinator-invitations/accept",
        json={
            "token": token,
            "name": "Second Attempt",
            "password": "InvitedCoordinator123!",
            "confirm_password": "InvitedCoordinator123!",
        },
    )
    assert replay.status_code == 400


def test_coordinator_invitation_expiry_is_enforced(
    test_client,
    test_student,
    monkeypatch,
):
    import main
    from auth.dependencies import get_db
    import models

    sent_invitations = []
    monkeypatch.setattr(
        main,
        "send_coordinator_invitation_email",
        lambda *args: sent_invitations.append(args),
    )
    _create_test_user("admin", "expired-invite-admin@example.com")
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Expiring invite",
            "description": "Invitation expiry coverage.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    admin_csrf = _login_and_get_csrf(
        test_client,
        "expired-invite-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_email": "expired@example.edu"},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200
    token = sent_invitations[0][1]

    db = next(app.dependency_overrides[get_db]())
    try:
        invitation = db.query(models.CoordinatorInvitation).filter_by(
            email="expired@example.edu"
        ).one()
        invitation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = test_client.post(
        "/api/v1/coordinator-invitations/accept",
        json={
            "token": token,
            "name": "Expired Coordinator",
            "password": "ExpiredCoordinator123!",
            "confirm_password": "ExpiredCoordinator123!",
        },
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


def test_coordinator_invitation_delivery_failure_preserves_prior_assignment(
    test_client,
    test_student,
    monkeypatch,
):
    import smtplib
    import main
    from auth.dependencies import get_db
    import models

    _create_test_user("admin", "delivery-admin@example.com")
    previous_coordinator_id = _create_test_user(
        "coordinator",
        "previous-coordinator@example.edu",
    )
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Delivery failure case",
            "description": "The previous assignment must be preserved.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    admin_csrf = _login_and_get_csrf(test_client, "delivery-admin@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_email": "previous-coordinator@example.edu"},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    def fail_delivery(*_args):
        raise smtplib.SMTPException("simulated email transport failure")

    monkeypatch.setattr(main, "send_coordinator_invitation_email", fail_delivery)
    response = test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_email": "new-coordinator@example.edu"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 503
    assert "not changed" in response.json()["detail"]
    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.query(models.Case).filter_by(id=case["id"]).one().assigned_coordinator_id == previous_coordinator_id
        assert db.query(models.CoordinatorInvitation).filter_by(
            email="new-coordinator@example.edu"
        ).count() == 0
    finally:
        db.close()


def test_coordinator_emails_include_only_minimal_case_details(monkeypatch):
    import auth.email_verification as email_verification

    messages = []
    monkeypatch.setattr(email_verification, "send_email", messages.append)
    email_verification.send_coordinator_assignment_email(
        "coordinator@example.edu",
        42,
        "academic",
    )
    email_verification.send_coordinator_invitation_email(
        "invite@example.edu",
        "single-use-token-value",
        42,
        "academic",
    )

    assert len(messages) == 2
    for message in messages:
        body = message.get_content()
        assert "case #42" in body
        assert "academic" in body
        assert "http://localhost:5173/login" in body
        assert "student@example.edu.in" not in body
        assert "private title" not in body
        assert "protected report details" not in body
    invitation_body = messages[1].get_content()
    assert "/coordinator-invitation?token=single-use-token-value" in invitation_body
    assert "dashboard/coordinator" in invitation_body


def test_coordinator_cannot_update_another_coordinators_case(
    test_client,
    test_student,
):
    # Create a student case
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )

    case_response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Private coordinator case",
            "description": "Only its assigned coordinator may update it.",
        },
        headers={"X-CSRF-Token": student_csrf},
    )

    assert case_response.status_code == 201
    case_id = case_response.json()["id"]

    # Create an admin and two different coordinators
    _create_test_user(
        role="admin",
        email="admin-scope@example.com",
    )

    assigned_coordinator_id = _create_test_user(
        role="coordinator",
        email="assigned-coordinator@example.com",
    )

    other_coordinator_id = _create_test_user(
        role="coordinator",
        email="other-coordinator@example.com",
    )

    # Admin assigns the case to the first coordinator
    admin_csrf = _login_and_get_csrf(
        test_client,
        "admin-scope@example.com",
    )

    assignment = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_id": assigned_coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    )

    assert assignment.status_code == 200

    # The other coordinator must not be able to update it
    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "other-coordinator@example.com",
    )

    response = test_client.patch(
        f"/api/v1/coordinator/cases/{case_id}/status",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": coordinator_csrf},
    )

    assert response.status_code == 404
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case_id}"
    ).status_code == 404

    admin_csrf = _login_and_get_csrf(
        test_client,
        "admin-scope@example.com",
    )
    reassignment = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_email": "other-coordinator@example.com"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert reassignment.status_code == 200
    assert reassignment.json()["case"]["assigned_coordinator_id"] == (
        other_coordinator_id
    )

    _login_and_get_csrf(test_client, "assigned-coordinator@example.com")
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case_id}"
    ).status_code == 404
    _login_and_get_csrf(test_client, "other-coordinator@example.com")
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case_id}"
    ).status_code == 200


def test_non_student_roles_are_denied_student_case_apis(
    test_client,
):
    for role, email, department in (
        ("coordinator", "deny-coordinator@example.com", None),
        ("admin", "deny-admin@example.com", None),
        ("department_staff", "deny-staff@example.com", "CSE"),
    ):
        _create_test_user(role, email, department=department)
        _login_and_get_csrf(test_client, email)

        assert test_client.get("/api/v1/cases").status_code == 403
        assert test_client.get("/api/v1/notifications").status_code == 403


def test_coordinator_scope_and_identity_fields(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case_response = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Private student title",
            "description": "Sensitive student report description.",
        },
        headers={"X-CSRF-Token": student_csrf},
    )
    case_id = case_response.json()["id"]

    coordinator_id = _create_test_user(
        "coordinator",
        "assigned-view@example.com",
    )
    _create_test_user(
        "admin",
        "admin-view@example.com",
    )
    admin_csrf = _login_and_get_csrf(
        test_client,
        "admin-view@example.com",
    )
    assignment = test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert assignment.status_code == 200
    assert "description" not in assignment.json()["case"]
    assert "student_id" not in assignment.json()["case"]

    _login_and_get_csrf(test_client, "assigned-view@example.com")
    response = test_client.get(
        f"/api/v1/coordinator/cases/{case_id}",
    )
    assert response.status_code == 200
    assert "description" not in response.json()
    assert "title" not in response.json()
    assert "Sensitive student report description." not in response.text
    assert "student_id" not in response.json()
    assert "student_email" not in response.json()


def test_test_database_uses_sqlite():
    from database import engine

    assert engine.dialect.name == "sqlite"


def test_profile_is_backend_sourced_and_role_fields_are_immutable(
    test_client,
    test_student,
):
    csrf_token = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )

    profile = test_client.get("/api/v1/auth/me")
    assert profile.status_code == 200
    assert profile.json()["role"] == "student"
    assert profile.json()["email"] == test_student["email"]
    assert profile.json()["created_at"]

    update = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Student"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Updated Student"
    assert update.json()["role"] == "student"
    assert update.json()["phone"] is None

    phone_update = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Student", "phone": "9876543210"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert phone_update.status_code == 200
    assert phone_update.json()["phone"] == "+919876543210"

    name_only_update = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Name Only Update"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert name_only_update.status_code == 200
    assert name_only_update.json()["phone"] == "+919876543210"

    invalid_phone_update = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Student", "phone": "123"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert invalid_phone_update.status_code == 422

    escalation = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Student", "role": "admin"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert escalation.status_code == 422

    department_escalation = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Student", "department": "CSE"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert department_escalation.status_code == 422

    without_csrf = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "No CSRF"},
    )
    assert without_csrf.status_code == 403


@pytest.mark.parametrize(
    ("role", "email"),
    [
        ("admin", "immutable-admin@example.com"),
        ("coordinator", "immutable-coordinator@example.com"),
    ],
)
def test_privileged_profile_update_cannot_change_role(
    test_client,
    role,
    email,
):
    _create_test_user(role, email)
    csrf_token = _login_and_get_csrf(test_client, email)
    response = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Attempted Escalation", "role": "admin"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 422
    assert test_client.get("/api/v1/auth/me").json()["role"] == role


def test_anonymous_case_cannot_disclose_identity_even_with_consent(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Anonymous case",
            "description": "Anonymous case details remain private.",
            "identity_mode": "restricted",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    coordinator_id = _create_test_user(
        "coordinator",
        "anonymous-coordinator@example.com",
    )
    _create_test_user("admin", "anonymous-admin@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "anonymous-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    consent = test_client.post(
        f"/api/v1/cases/{case['id']}/consent",
        json={
            "purpose": "Support contact",
            "recipient": "anonymous-coordinator@example.com",
            "scope": "Contact for follow-up",
        },
        headers={"X-CSRF-Token": student_csrf},
    )
    assert consent.status_code == 201

    anonymous_mode = test_client.patch(
        f"/api/v1/cases/{case['id']}/identity",
        json={"identity_mode": "anonymous"},
        headers={"X-CSRF-Token": student_csrf},
    )
    assert anonymous_mode.status_code == 200

    denied_new_consent = test_client.post(
        f"/api/v1/cases/{case['id']}/consent",
        json={
            "purpose": "New support contact",
            "recipient": "anonymous-coordinator@example.com",
            "scope": "Contact for follow-up",
        },
        headers={"X-CSRF-Token": student_csrf},
    )
    assert denied_new_consent.status_code == 403

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "anonymous-coordinator@example.com",
    )
    disclosure = test_client.post(
        f"/api/v1/coordinator/cases/{case['id']}/identity-disclosure",
        json={
            "purpose": "Support contact",
            "scope": "Contact for follow-up",
        },
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert disclosure.status_code == 403

    admin_csrf = _login_and_get_csrf(
        test_client,
        "anonymous-admin@example.com",
    )
    admin_disclosure = test_client.post(
        f"/api/v1/coordinator/cases/{case['id']}/identity-disclosure",
        json={
            "purpose": "Support contact",
            "scope": "Contact for follow-up",
        },
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert admin_disclosure.status_code == 403


def test_department_assignment_and_isolation_redact_student_data(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case_one = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Private identity title",
            "description": "Free text that department staff must not see.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    case_two = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Unrouted title",
            "description": "Unrouted free-text details.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()

    _create_test_user(
        "department_staff",
        "cse-staff@example.com",
        department="CSE",
    )
    _create_test_user(
        "department_staff",
        "eee-staff@example.com",
        department="EEE",
    )
    _create_test_user("admin", "department-admin@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "department-admin@example.com",
    )
    route_response = test_client.patch(
        f"/api/v1/cases/{case_one['id']}/department",
        json={"department": "cSe"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert route_response.status_code == 200
    assert route_response.json()["case"]["department"] == "CSE"
    invalid_route = test_client.patch(
        f"/api/v1/cases/{case_two['id']}/department",
        json={"department": "Unprovisioned"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert invalid_route.status_code == 400

    staff_login = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "cse-staff@example.com",
            "password": "TestPassword123!",
        },
    )
    assert staff_login.status_code == 200
    assert staff_login.json()["user"]["role"] == "department_staff"
    assert staff_login.json()["user"]["department"] == "CSE"
    staff_csrf = staff_login.json()["csrf_token"]
    cases = test_client.get("/api/v1/department/cases").json()
    assert [item["id"] for item in cases] == [case_one["id"]]
    assert set(cases[0]) == {"id", "category", "status", "created_at"}
    assert test_client.get(
        f"/api/v1/department/cases/{case_two['id']}"
    ).status_code == 404
    assert test_client.get("/api/v1/cases").status_code == 403
    assert test_client.get("/api/v1/admin/cases").status_code == 403
    assert test_client.get("/api/v1/coordinator/cases").status_code == 403
    assert test_client.get("/api/v1/departments").status_code == 403

    assert test_client.post("/api/v1/auth/logout").status_code == 403
    assert test_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": staff_csrf},
    ).status_code == 200
    assert test_client.get("/api/v1/department/cases").status_code == 401

    _login_and_get_csrf(test_client, "eee-staff@example.com")
    assert test_client.get("/api/v1/department/cases").json() == []


def test_assigned_coordinator_routes_case_to_authorized_department(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Private routing title",
            "description": "Confidential description is not visible to staff.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    coordinator_id = _create_test_user(
        "coordinator",
        "routing-coordinator@example.com",
    )
    other_coordinator_id = _create_test_user(
        "coordinator",
        "other-routing-coordinator@example.com",
    )
    _create_test_user(
        "department_staff",
        "counselling-staff@example.com",
        department="Counselling",
    )
    _create_test_user(
        "department_staff",
        "academic-staff@example.com",
        department="Academic Support",
    )
    _create_test_user("admin", "routing-admin@example.com")
    admin_csrf = _login_and_get_csrf(test_client, "routing-admin@example.com")
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "routing-coordinator@example.com",
    )
    assert set(test_client.get("/api/v1/departments").json()) == {
        "Academic Support",
        "Counselling",
    }
    route = test_client.patch(
        f"/api/v1/cases/{case['id']}/department",
        json={"department": "cOUNSELLING"},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert route.status_code == 200
    routed_case = route.json()["case"]
    assert routed_case["department"] == "Counselling"
    assert routed_case["category"] == "academic"
    assert "assigned_coordinator_id" not in routed_case
    assert "title" not in routed_case
    assert "description" not in routed_case
    assert "student_id" not in routed_case
    assert "Confidential description" not in route.text
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case['id']}"
    ).json()["department"] == "Counselling"

    invalid_route = test_client.patch(
        f"/api/v1/cases/{case['id']}/department",
        json={"department": "Unprovisioned"},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert invalid_route.status_code == 400
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/department",
        json={"department": "Academic Support"},
    ).status_code == 403
    escalation_attempt = test_client.patch(
        f"/api/v1/cases/{case['id']}/department",
        json={
            "department": "Academic Support",
            "role": "admin",
            "coordinator_id": other_coordinator_id,
        },
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert escalation_attempt.status_code == 422
    assert test_client.get(
        f"/api/v1/coordinator/cases/{case['id']}"
    ).json()["department"] == "Counselling"
    assert test_client.get("/api/v1/admin/cases").status_code == 403


def test_coordinator_cannot_route_another_coordinators_case(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Cross-coordinator routing",
            "description": "Only the assigned coordinator can route this case.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    assigned_coordinator_id = _create_test_user(
        "coordinator",
        "assigned-routing@example.com",
    )
    _create_test_user(
        "coordinator",
        "unassigned-routing@example.com",
    )
    _create_test_user(
        "department_staff",
        "routing-staff@example.com",
        department="Counselling",
    )
    _create_test_user("admin", "cross-routing-admin@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "cross-routing-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": assigned_coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    unassigned_csrf = _login_and_get_csrf(
        test_client,
        "unassigned-routing@example.com",
    )
    denied = test_client.patch(
        f"/api/v1/cases/{case['id']}/department",
        json={"department": "Counselling"},
        headers={"X-CSRF-Token": unassigned_csrf},
    )
    assert denied.status_code == 404


def test_department_rerouting_revokes_previous_department_access_and_preserves_coordinator(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case = test_client.post(
        "/api/v1/cases",
        json={
            "category": "wellbeing",
            "title": "Department reassignment title",
            "description": "Department access must move without altering coordinator assignment.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()
    coordinator_id = _create_test_user(
        "coordinator",
        "department-reassignment-coordinator@example.com",
    )
    _create_test_user(
        "department_staff",
        "old-department-staff@example.com",
        department="Old Department",
    )
    _create_test_user(
        "department_staff",
        "new-department-staff@example.com",
        department="New Department",
    )
    _create_test_user("admin", "department-reassignment-admin@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "department-reassignment-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case['id']}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200
    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "department-reassignment-coordinator@example.com",
    )
    for department in ("Old Department", "New Department"):
        assert test_client.patch(
            f"/api/v1/cases/{case['id']}/department",
            json={"department": department},
            headers={"X-CSRF-Token": coordinator_csrf},
        ).status_code == 200

    _login_and_get_csrf(test_client, "old-department-staff@example.com")
    assert test_client.get("/api/v1/department/cases").json() == []
    assert test_client.get(
        f"/api/v1/department/cases/{case['id']}"
    ).status_code == 404
    _login_and_get_csrf(test_client, "new-department-staff@example.com")
    department_case = test_client.get(
        f"/api/v1/department/cases/{case['id']}"
    )
    assert department_case.status_code == 200
    assert department_case.json()["category"] == "wellbeing"
    assert set(department_case.json()) == {"id", "category", "status", "created_at"}
    assert "Department reassignment title" not in department_case.text
    assert "must move without altering" not in department_case.text

    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        stored_case = db.query(models.Case).filter_by(id=case["id"]).one()
        assert stored_case.assigned_coordinator_id == coordinator_id
        assert stored_case.department == "New Department"
    finally:
        db.close()


def test_admin_case_list_does_not_expose_identity_or_report_text(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Hidden title",
            "description": "Hidden sensitive description.",
        },
        headers={"X-CSRF-Token": student_csrf},
    )

    _create_test_user("admin", "safe-admin@example.com")
    _login_and_get_csrf(test_client, "safe-admin@example.com")
    cases = test_client.get("/api/v1/admin/cases")
    assert cases.status_code == 200
    assert "title" not in cases.json()[0]
    assert "description" not in cases.json()[0]
    assert "student_id" not in cases.json()[0]
    assert test_client.get("/api/v1/cases").status_code == 403


def test_identity_disclosure_requires_active_exact_student_consent(
    test_client,
    test_student,
):
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    case_id = test_client.post(
        "/api/v1/cases",
        json={
            "category": "academic",
            "title": "Consent case",
            "description": "A private report with consent checks.",
        },
        headers={"X-CSRF-Token": student_csrf},
    ).json()["id"]
    coordinator_id = _create_test_user(
        "coordinator",
        "consent-coordinator@example.com",
    )
    _create_test_user("admin", "consent-admin@example.com")
    admin_csrf = _login_and_get_csrf(
        test_client,
        "consent-admin@example.com",
    )
    assert test_client.patch(
        f"/api/v1/cases/{case_id}/assign",
        json={"coordinator_id": coordinator_id},
        headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    purpose = "Wellbeing follow-up"
    scope = "Contact student to arrange support"
    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    wrong_recipient = test_client.post(
        f"/api/v1/cases/{case_id}/consent",
        json={
            "purpose": purpose,
            "recipient": "someone-else@example.com",
            "scope": scope,
        },
        headers={"X-CSRF-Token": student_csrf},
    )
    assert wrong_recipient.status_code == 400

    consent = test_client.post(
        f"/api/v1/cases/{case_id}/consent",
        json={
            "purpose": purpose,
            "recipient": "consent-coordinator@example.com",
            "scope": scope,
        },
        headers={"X-CSRF-Token": student_csrf},
    )
    assert consent.status_code == 201

    admin_csrf = _login_and_get_csrf(
        test_client,
        "consent-admin@example.com",
    )
    admin_disclosure = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": purpose, "scope": scope},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert admin_disclosure.status_code == 403

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "consent-coordinator@example.com",
    )
    wrong_purpose = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": "Different purpose", "scope": scope},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert wrong_purpose.status_code == 403
    wrong_scope = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": purpose, "scope": "Different scope"},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert wrong_scope.status_code == 403

    from auth.dependencies import get_db
    import models

    db = next(app.dependency_overrides[get_db]())
    try:
        consent_record = (
            db.query(models.CaseConsent)
            .filter(models.CaseConsent.case_id == case_id)
            .first()
        )
        assert consent_record is not None
        valid_granted_at = consent_record.granted_at
        consent_record.granted_at = None
        db.commit()
    finally:
        db.close()

    invalid_grant_time = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": purpose, "scope": scope},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert invalid_grant_time.status_code == 403

    db = next(app.dependency_overrides[get_db]())
    try:
        consent_record = (
            db.query(models.CaseConsent)
            .filter(models.CaseConsent.case_id == case_id)
            .first()
        )
        assert consent_record is not None
        consent_record.granted_at = valid_granted_at
        db.commit()
    finally:
        db.close()

    disclosure = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": purpose, "scope": scope},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert disclosure.status_code == 200
    assert disclosure.json()["student_email"] == test_student["email"]

    student_csrf = _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    consent_id = test_client.get(
        f"/api/v1/cases/{case_id}/consent"
    ).json()[0]["id"]
    withdrawn = test_client.patch(
        f"/api/v1/cases/{case_id}/consent/{consent_id}/withdraw",
        headers={"X-CSRF-Token": student_csrf},
    )
    assert withdrawn.status_code == 200

    coordinator_csrf = _login_and_get_csrf(
        test_client,
        "consent-coordinator@example.com",
    )
    after_withdrawal = test_client.post(
        f"/api/v1/coordinator/cases/{case_id}/identity-disclosure",
        json={"purpose": purpose, "scope": scope},
        headers={"X-CSRF-Token": coordinator_csrf},
    )
    assert after_withdrawal.status_code == 403
    _login_and_get_csrf(
        test_client,
        test_student["email"],
        test_student["password"],
    )
    audit = test_client.get(
        f"/api/v1/cases/{case_id}/disclosure-audit"
    )
    assert audit.status_code == 200
    decisions = {entry["decision"] for entry in audit.json()}
    assert {"consent_granted", "denied", "allowed", "consent_withdrawn"} <= decisions


def test_unsafe_case_assignment_rejects_invalid_csrf(
    test_client,
):
    _create_test_user("admin", "csrf-admin@example.com")
    _login_and_get_csrf(test_client, "csrf-admin@example.com")
    response = test_client.patch(
        "/api/v1/cases/1/assign",
        json={"coordinator_id": 999},
        headers={"X-CSRF-Token": "incorrect-token"},
    )
    assert response.status_code == 403
