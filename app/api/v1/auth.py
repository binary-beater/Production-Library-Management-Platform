"""API Router controllers managing user registration, login, token refresh, logout, and /me profile requests."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.dependencies.auth import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    ClientMetadata,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def parse_device_name(user_agent: str | None) -> str:
    """Derive device context category name from User-Agent string (e.g. Chrome on Windows).

    Args:
        user_agent: The raw request User-Agent header value.

    Returns:
        A derived human-readable device identifier name string.
    """
    if not user_agent:
        return "Unknown Device"

    ua = user_agent.lower()

    # Simple User-Agent categorization logic
    browser = "Unknown Browser"
    if "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "edge" in ua:
        browser = "Edge"

    os = "Unknown OS"
    if "windows" in os or "win64" in ua or "wow64" in ua:
        os = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os = "macOS"
    elif "linux" in ua:
        os = "Linux"
    elif "android" in ua:
        os = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os = "iOS"

    return f"{browser} on {os}"


@router.post(
    "/register",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    dto: UserRegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Register a new library user account and auto-create member profile."""
    return await auth_service.register(dto)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    dto: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> TokenResponse:
    """Authenticate user credentials and issue Access and Stateful Refresh tokens."""
    # Resolve Client Metadata parameters
    ip_address = request.client.host if request.client else "127.0.0.1"
    device_name = parse_device_name(user_agent)

    metadata = ClientMetadata(
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_name,
    )

    access_token, refresh_token = await auth_service.login(dto, metadata)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    dto: TokenRefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> TokenResponse:
    """Request new rotated Access and Refresh tokens using valid raw Refresh token."""
    ip_address = request.client.host if request.client else "127.0.0.1"
    device_name = parse_device_name(user_agent)

    metadata = ClientMetadata(
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_name,
    )

    access_token, refresh_token = await auth_service.refresh_token(dto.refresh_token, metadata)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    dto: TokenRefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Revoke the current Refresh token session invalidating it."""
    await auth_service.logout(dto.refresh_token)


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Retrieve profile and permissions information for the currently authenticated user."""
    return current_user
