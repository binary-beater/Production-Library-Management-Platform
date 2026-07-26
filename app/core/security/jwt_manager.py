"""Module for implementing JWT access token creation and validation with clock skew margin."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt


class JWTManager:
    """Manager for generating and verifying JSON Web Tokens (JWT) using python-jose."""

    def __init__(
        self,
        signing_key: str,
        verification_key: str | None = None,
        algorithm: str = "HS256",
        issuer: str = "app",
        audience: str = "app:users",
        access_token_expire_minutes: int = 15,
    ) -> None:
        """Initialize the JWTManager.

        Args:
            signing_key: The key used to sign tokens (symmetric secret or private key).
            verification_key: Optional key to verify tokens (public key). If None, signing_key is used.
            algorithm: The signing algorithm to use (default: HS256).
            issuer: Expected issuer of the token ('iss' claim).
            audience: Expected audience of the token ('aud' claim).
            access_token_expire_minutes: Token expiration time in minutes.
        """
        self.signing_key = signing_key
        self.verification_key = verification_key or signing_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(
        self,
        subject: str,
        jti: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a signed JWT access token.

        Args:
            subject: The subject of the token (typically the user ID).
            jti: Unique identifier (UUIDv4) for the token.
            additional_claims: Optional dictionary of additional claims.

        Returns:
            The encoded JWT string.
        """
        now = datetime.now(UTC)
        claims = {
            "sub": subject,
            "jti": jti,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
        }
        if additional_claims:
            claims.update(additional_claims)

        return str(jwt.encode(claims, self.signing_key, algorithm=self.algorithm))

    def decode_and_validate_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT access token.

        Executes the following validation sequence:
        1. Verify Signature
        2. Verify Expiry (exp)
        3. Verify Not Before (nbf)
        4. Verify Audience (aud)
        5. Verify Issuer (iss)

        Args:
            token: The JWT token string to decode and validate.

        Returns:
            The decoded claims dictionary.

        Raises:
            JWTError: If signature, expiry, nbf, aud, iss, or other validation checks fail.
        """
        # Decode automatically verifies signature, exp, nbf, aud, and iss
        # leeway=60 provides a 60-second clock skew margin
        payload = jwt.decode(
            token,
            self.verification_key,
            algorithms=[self.algorithm],
            audience=self.audience,
            issuer=self.issuer,
            options={
                "require_aud": True,
                "require_iat": True,
                "require_exp": True,
                "require_nbf": True,
                "require_iss": True,
                "leeway": 60,
            },
        )

        # Enforce presence of all required claims
        required_claims = {"sub", "jti", "exp", "iss", "aud", "iat", "nbf"}
        if not required_claims.issubset(payload.keys()):
            missing_claims = required_claims - payload.keys()
            raise JWTError(f"Missing required claims: {missing_claims}")

        # Return type match dict[str, Any]
        return dict(payload)
