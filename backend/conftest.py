
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set this before importing the application: the module-level engine must
# never resolve credentials from .env or point at MySQL during test collection.
os.environ["MINDBRIDGE_TESTING"] = "1"
os.environ["APP_ENV"] = "test"
os.environ["COLLEGE_EMAIL_DOMAINS"] = "college.example.edu.in"
os.environ["OTP_HASH_SECRET"] = "test-only-secret-not-for-deployment-0000000000000000"
os.environ["SMTP_HOST"] = "smtp.test.invalid"
os.environ["SMTP_PORT"] = "1025"
os.environ["SMTP_FROM_EMAIL"] = "mindbridge@example.invalid"
os.environ["SMTP_USE_TLS"] = "false"
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""

from database import Base
from auth.dependencies import get_db
from main import app, reset_login_attempts
import models


@pytest.fixture
def test_client():
    reset_login_attempts()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        Base.metadata.create_all(bind=engine)
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        reset_login_attempts()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def suppress_coordinator_emails(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "send_coordinator_assignment_email",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        main,
        "send_coordinator_invitation_email",
        lambda *_args: None,
    )


@pytest.fixture
def test_student(test_client):
    from auth.security import hash_password

    db = next(app.dependency_overrides[get_db]())
    try:
        user = models.User(
            name="Test Student",
            email="student@college.example.edu.in",
            password_hash=hash_password("TestPassword123!"),
            role="student",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    return {
        "email": "student@college.example.edu.in",
        "password": "TestPassword123!",
    }
