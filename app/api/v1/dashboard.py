from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import RoleRequirement, get_dashboard_service
from app.domain.enums import UserRole
from app.schemas.book import APIResponse
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Operations Analytics"])


@router.get(
    "/summary",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleRequirement([UserRole.LIBRARIAN, UserRole.ADMIN]))],
)
async def get_dashboard_summary(
    days: Annotated[
        int,
        Query(
            description="Time-window query parameter (days count) for popular books and loans summary.",
            ge=1,
            le=365,
        ),
    ] = 30,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)] = None,
) -> APIResponse:
    """Retrieve operational analytics summary dashboard (Admin/Librarian access only)."""
    summary = await dashboard_service.get_summary(days)
    return APIResponse(
        success=True,
        message="Dashboard analytics summary retrieved successfully",
        data=DashboardSummaryResponse.model_validate(summary),
    )
