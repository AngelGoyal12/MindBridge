
from datetime import datetime
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from auth.roles import Role


def normalize_indian_phone(phone: str) -> str:
    compact = re.sub(r"[\s()-]", "", phone)
    if compact.startswith("+91"):
        national_number = compact[3:]
    elif compact.startswith("91") and len(compact) == 12:
        national_number = compact[2:]
    else:
        national_number = compact
    if not re.fullmatch(r"[6-9]\d{9}", national_number):
        raise ValueError(
            "Enter a valid 10-digit Indian mobile number, optionally with +91."
        )
    return f"+91{national_number}"


def validate_strong_password(password: str) -> str:
    requirements = (
        (len(password) >= 12, "at least 12 characters"),
        (re.search(r"[A-Z]", password) is not None, "an uppercase letter"),
        (re.search(r"[a-z]", password) is not None, "a lowercase letter"),
        (re.search(r"[0-9]", password) is not None, "a digit"),
        (re.search(r"[^A-Za-z0-9]", password) is not None, "a special character"),
    )
    missing = [label for satisfied, label in requirements if not satisfied]
    if missing:
        raise ValueError("Password must include " + ", ".join(missing) + ".")
    return password


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=16)
    department_course: str = Field(min_length=1, max_length=100)
    current_semester: int = Field(ge=1, le=8, strict=True)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, name: object) -> object:
        return name.strip() if isinstance(name, str) else name

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: object) -> object:
        return email.strip().lower() if isinstance(email, str) else email

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, phone: str) -> str:
        return normalize_indian_phone(phone)

    @field_validator("department_course", mode="before")
    @classmethod
    def trim_department_course(cls, department_course: object) -> object:
        return (
            department_course.strip()
            if isinstance(department_course, str)
            else department_course
        )

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, password: str) -> str:
        return validate_strong_password(password)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password must match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    department: str | None = None
    department_course: str | None = None
    current_semester: int | None = None
    phone: str | None = None
    created_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    phone: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, name: object) -> object:
        return name.strip() if isinstance(name, str) else name

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, phone: str | None) -> str | None:
        return normalize_indian_phone(phone) if phone is not None else None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class CaseCreate(BaseModel):
    category: str
    title: str
    description: str
    identity_mode: Literal["identified", "restricted", "anonymous"] = "identified"


class CaseIdentityUpdate(BaseModel):
    identity_mode: Literal["identified", "restricted", "anonymous"]
