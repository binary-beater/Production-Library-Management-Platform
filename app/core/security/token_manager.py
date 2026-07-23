"""Module for implementing raw refresh token generation and SHA-256 fingerprinting."""

import hashlib
import secrets


class TokenManager:
    """Manager for generating cryptographically secure random tokens and computing their fingerprints."""

    @staticmethod
    def generate_random_token() -> str:
        """Generate a cryptographically secure random token string.

        Uses secrets.token_urlsafe(64) to generate high-entropy strings suitable
        for refresh tokens.

        Returns:
            A cryptographically secure random token string.
        """
        return secrets.token_urlsafe(64)

    @staticmethod
    def generate_token_fingerprint(token: str) -> str:
        """Generate a hex-encoded SHA-256 fingerprint of the given token.

        Args:
            token: The raw token string.

        Returns:
            The SHA-256 hex-encoded hash string.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
