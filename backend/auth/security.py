
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password before storing it."""
    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    stored_hash: str,
) -> bool:
    """Verify a submitted password against its stored hash."""
    if not plain_password or not stored_hash:
        return False

    try:
        return password_hasher.verify(
            plain_password,
            stored_hash,
        )
    except (ValueError, TypeError):
        return False
