import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.dependencies.auth import (
    RoleRequirement,
    get_current_user,
    get_reservation_service,
)
from app.domain.enums import UserRole
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.schemas.reservation import (
    APIResponse,
    ReservationCreateRequest,
    ReservationDetailResponse,
    ReservationResponse,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleRequirement([UserRole.MEMBER]))],
)
async def place_reservation(
    dto: ReservationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    """Place a reservation hold on a book that is currently out of stock (Members only)."""
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(current_user.id)
    if not member:
        raise ForbiddenException("User does not have an active Member profile")

    res = await reservation_service.place_reservation(member.id, dto.book_id)

    # Compute queue position dynamically
    pos = None
    if res.status == "PENDING":
        pos = await reservation_service.reservation_repo.compute_queue_position(
            res.book_id, res.reserved_at
        )

    res_response = ReservationResponse.model_validate(res)
    res_response.queue_position = pos

    return APIResponse(
        success=True,
        message="Book reservation placed successfully",
        data=res_response,
    )


@router.post(
    "/{id}/cancel",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleRequirement([UserRole.MEMBER]))],
)
async def cancel_reservation(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    """Soft-cancel a pending/hold reservation and immediately promote the next inline user."""
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(current_user.id)
    if not member:
        raise ForbiddenException("User does not have an active Member profile")

    res = await reservation_service.cancel_reservation(id, member.id)
    return APIResponse(
        success=True,
        message="Reservation cancelled successfully",
        data=ReservationResponse.model_validate(res),
    )


@router.get(
    "/active",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleRequirement([UserRole.MEMBER]))],
)
async def list_active_reservations(
    current_user: Annotated[User, Depends(get_current_user)],
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    """List all active (PENDING/HOLD) reservations for the authenticated member."""
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(current_user.id)
    if not member:
        raise ForbiddenException("User does not have an active Member profile")

    results = await reservation_service.get_active_reservations(member.id)
    serialized = [ReservationDetailResponse.model_validate(r) for r in results]
    # Set dynamic queue positions explicitly on responses
    for i, r in enumerate(results):
        serialized[i].queue_position = r["queue_position"]

    return APIResponse(
        success=True,
        message="Active reservations retrieved successfully",
        data=serialized,
    )


@router.post(
    "/sweep",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleRequirement([UserRole.LIBRARIAN, UserRole.ADMIN]))],
)
async def sweep_expired_holds(
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
) -> APIResponse:
    """Sweep expired reservation holds and promote next members (Admin/Librarian only)."""
    expired_count = await reservation_service.process_expired_holds()
    return APIResponse(
        success=True,
        message="Expired holds processed successfully",
        data={"expired_count": expired_count},
    )
