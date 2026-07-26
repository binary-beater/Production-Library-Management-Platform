"""Module for securely hashing and verifying passwords using Argon2id."""

from passlib.context import CryptContext


class PasswordHasher:
    """Manager for securely hashing and verifying passwords using Argon2id."""

    def __init__(self) -> None:
        """Initialize the password hasher with Argon2id algorithm."""
        self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id.

        Args:
            password: The plain text password to hash.

        Returns:
            The hashed password string.
        """
        return str(self.pwd_context.hash(password))

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash.

        Args:
            plain_password: The plain text password.
            hashed_password: The hashed password to compare against.

        Returns:
            True if the password matches the hash, False otherwise.
        """
        return bool(self.pwd_context.verify(plain_password, hashed_password))
