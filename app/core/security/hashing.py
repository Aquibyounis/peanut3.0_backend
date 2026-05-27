"""
Password hashing utilities using passlib + bcrypt.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password and return the bcrypt digest."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches the *hashed* bcrypt digest."""
    return _pwd_context.verify(plain, hashed)
