import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlparse

from fastapi import HTTPException

from models import PendingEmailVerification


def otp_settings() -> tuple[int, int, int, int]:
    try:
        expiration = int(os.getenv("OTP_EXPIRATION_SECONDS", "300"))
        cooldown = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
        resend_limit = int(os.getenv("OTP_MAX_RESENDS", "5"))
        attempt_limit = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    except ValueError as error:
        raise RuntimeError("OTP settings must be integers.") from error
    if not 60 <= expiration <= 1800:
        raise RuntimeError("OTP_EXPIRATION_SECONDS must be from 60 to 1800.")
    if not 30 <= cooldown <= 3600:
        raise RuntimeError("OTP_RESEND_COOLDOWN_SECONDS must be from 30 to 3600.")
    if not 1 <= resend_limit <= 20:
        raise RuntimeError("OTP_MAX_RESENDS must be from 1 to 20.")
    if not 1 <= attempt_limit <= 20:
        raise RuntimeError("OTP_MAX_ATTEMPTS must be from 1 to 20.")
    return expiration, cooldown, resend_limit, attempt_limit


def college_email_domains() -> tuple[str, ...]:
    configured_domains = os.getenv("COLLEGE_EMAIL_DOMAINS", "").strip()
    if not configured_domains:
        configured_domains = os.getenv("COLLEGE_EMAIL_DOMAIN", "").strip()
    domains = tuple(
        domain.strip().lower().lstrip("@")
        for domain in configured_domains.split(",")
        if domain.strip()
    )
    if any(
        not domain.endswith(".edu.in")
        or any(char.isspace() for char in domain)
        or "@" in domain
        for domain in domains
    ):
        raise HTTPException(
            status_code=503,
            detail="Configured college email domains must end in .edu.in.",
        )
    return domains


def validate_college_email(email: str) -> bool:
    normalized = email.strip().lower()
    if normalized.count("@") != 1:
        return False
    domain = normalized.rsplit("@", 1)[-1]
    if not domain.endswith(".edu.in"):
        return False
    allowed_domains = college_email_domains()
    return not allowed_domains or domain in allowed_domains


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, otp: str) -> str:
    secret = os.getenv("OTP_HASH_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Email verification is not configured.",
        )
    message = f"{email.strip().lower()}:{otp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def otp_matches(pending: PendingEmailVerification, otp: str) -> bool:
    try:
        candidate = hash_otp(pending.email, otp)
    except HTTPException:
        raise
    return hmac.compare_digest(candidate, pending.otp_hash)


def smtp_settings() -> tuple[str, int, str, bool, str, str]:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not host or not sender:
        raise RuntimeError(
            "SMTP_HOST and SMTP_FROM_EMAIL must be configured for email verification."
        )
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("SMTP_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("SMTP_PORT is outside the valid port range.")

    tls_setting = os.getenv("SMTP_USE_TLS", "true").strip().lower()
    if tls_setting not in {"true", "false"}:
        raise RuntimeError("SMTP_USE_TLS must be true or false.")
    use_tls = tls_setting == "true"
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    if username and not password:
        raise RuntimeError("SMTP_PASSWORD is required with SMTP_USERNAME.")
    if username and not use_tls:
        raise RuntimeError("SMTP_USE_TLS must be true when SMTP authentication is enabled.")
    return host, port, sender, use_tls, username, password


def validate_smtp_configuration() -> None:
    smtp_settings()


def frontend_base_url() -> str:
    configured_url = os.getenv("FRONTEND_URL", "").strip()
    if not configured_url:
        origins = os.getenv("FRONTEND_ORIGINS", "").split(",")
        configured_url = next(
            (origin.strip() for origin in origins if origin.strip()),
            "http://localhost:5173",
        )
    parsed_url = urlparse(configured_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.path not in {"", "/"}
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RuntimeError("FRONTEND_URL must be an http(s) origin.")
    return configured_url.rstrip("/")


def coordinator_invitation_expiration() -> int:
    try:
        hours = int(os.getenv("COORDINATOR_INVITATION_EXPIRATION_HOURS", "72"))
    except ValueError as error:
        raise RuntimeError(
            "COORDINATOR_INVITATION_EXPIRATION_HOURS must be an integer."
        ) from error
    if not 1 <= hours <= 168:
        raise RuntimeError(
            "COORDINATOR_INVITATION_EXPIRATION_HOURS must be from 1 to 168."
        )
    return hours


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_email(message: EmailMessage) -> None:
    host, port, _sender, use_tls, username, password = smtp_settings()
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls(context=context)
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def send_coordinator_assignment_email(
    email: str,
    case_id: int,
    category: str,
) -> None:
    base_url = frontend_base_url()
    message = EmailMessage()
    message["Subject"] = f"MindBridge case assignment: #{case_id}"
    message["From"] = smtp_settings()[2]
    message["To"] = email
    message.set_content(
        f"You have been assigned MindBridge case #{case_id} "
        f"(category: {category}).\n\n"
        f"Sign in to view your assigned cases: {base_url}/login\n"
        f"Coordinator dashboard: {base_url}/dashboard/coordinator\n\n"
        "Case details and student identity are intentionally not included "
        "in this email."
    )
    send_email(message)


def send_coordinator_invitation_email(
    email: str,
    token: str,
    case_id: int,
    category: str,
) -> None:
    base_url = frontend_base_url()
    message = EmailMessage()
    message["Subject"] = "Invitation to MindBridge coordinator access"
    message["From"] = smtp_settings()[2]
    message["To"] = email
    message.set_content(
        f"You have been invited to coordinate MindBridge case #{case_id} "
        f"(category: {category}).\n\n"
        "Set your password and activate your coordinator account using "
        f"this single-use link: {base_url}/coordinator-invitation"
        f"?token={token}\n\n"
        f"After activation, sign in at {base_url}/login and open "
        f"{base_url}/dashboard/coordinator.\n\n"
        "This invitation expires soon. Case details and student identity "
        "are intentionally not included in this email."
    )
    send_email(message)


def send_verification_email(email: str, otp: str, expiration_seconds: int) -> None:
    sender = smtp_settings()[2]
    message = EmailMessage()
    message["Subject"] = "MindBridge email verification"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "Use this one-time code to verify your MindBridge account: "
        f"{otp}\n\nThe code expires in {expiration_seconds // 60} minutes. "
        "If you did not request this, you can ignore this message."
    )

    send_email(message)


def prepare_verification(email: str, otp: str) -> tuple[str, datetime]:
    expiration_seconds, _, _, _ = otp_settings()
    return hash_otp(email, otp), datetime.now(timezone.utc) + timedelta(
        seconds=expiration_seconds
    )
