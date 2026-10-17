import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from auth.roles import Role
from auth.security import hash_password
from auth.schemas import validate_strong_password
from database import SessionLocal
from models import User


PRIVILEGED_ROLES = (
    Role.COORDINATOR.value,
    Role.ADMIN.value,
    Role.DEPARTMENT_STAFF.value,
)


def _validate_provisioning_fields(
    name: str,
    role: str,
    department: str | None,
    password: str,
) -> None:
    if not 2 <= len(name) <= 100:
        raise ValueError("name must contain 2 to 100 characters")
    if role not in PRIVILEGED_ROLES:
        raise ValueError("role must be a privileged MindBridge role")
    if role == Role.DEPARTMENT_STAFF.value and not department:
        raise ValueError("department staff accounts require --department")
    if role != Role.DEPARTMENT_STAFF.value and department:
        raise ValueError("--department is only valid for department staff")
    if department and len(department) > 100:
        raise ValueError("department must not exceed 100 characters")
    validate_strong_password(password)
    if len(password) > 128:
        raise ValueError("password must not exceed 128 characters")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a privileged MindBridge account."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=PRIVILEGED_ROLES)
    parser.add_argument("--department")
    args = parser.parse_args()

    name = args.name.strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(args.email.strip())).lower()
    except ValidationError:
        parser.error("email must be a valid address")

    department = (
        args.department.strip()
        if args.department and args.department.strip()
        else None
    )

    password = getpass("Password (12-128 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("passwords do not match")
    try:
        _validate_provisioning_fields(name, args.role, department, password)
    except ValueError as error:
        parser.error(str(error))

    with SessionLocal() as db:
        existing_user = db.query(User.id).filter(User.email == email).first()
        if existing_user:
            parser.error("an account with this email already exists")

        if args.role == Role.DEPARTMENT_STAFF.value and department:
            provisioned_departments = (
                db.query(User.department)
                .filter(
                    User.role == Role.DEPARTMENT_STAFF.value,
                    User.department.is_not(None),
                )
                .order_by(func.lower(User.department), User.department)
                .all()
            )
            department = next(
                (
                    existing_department.strip()
                    for (existing_department,) in provisioned_departments
                    if existing_department
                    and existing_department.strip().casefold()
                    == department.casefold()
                ),
                department,
            )

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=args.role,
            department=department,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.error("an account with this email already exists")

    print(f"Created {args.role} account for {email}.")


if __name__ == "__main__":
    main()
