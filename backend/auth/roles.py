from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    COORDINATOR = "coordinator"
    ADMIN = "admin"
    DEPARTMENT_STAFF = "department_staff"


ROLE_VALUES = frozenset(role.value for role in Role)
