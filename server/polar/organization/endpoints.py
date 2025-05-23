from uuid import UUID

import structlog
from fastapi import Depends, Query

from polar.account.schemas import Account as AccountSchema
from polar.account.service import account as account_service
from polar.authz.service import AccessType, Authz
from polar.exceptions import (
    NotPermitted,
    ResourceNotFound,
    Unauthorized,
)
from polar.kit.pagination import ListResource, Pagination, PaginationParamsQuery
from polar.models import Account, Organization
from polar.openapi import APITag
from polar.postgres import AsyncSession, get_db_session
from polar.routing import APIRouter
from polar.user_organization.schemas import OrganizationMember
from polar.user_organization.service import (
    user_organization as user_organization_service,
)

from . import auth, sorting
from .schemas import (
    Organization as OrganizationSchema,
)
from .schemas import (
    OrganizationCreate,
    OrganizationID,
    OrganizationSetAccount,
    OrganizationUpdate,
)
from .service import organization as organization_service

log = structlog.get_logger()

router = APIRouter(prefix="/organizations", tags=["organizations"])

OrganizationNotFound = {
    "description": "Organization not found.",
    "model": ResourceNotFound.schema(),
}


@router.get(
    "/",
    summary="List Organizations",
    response_model=ListResource[OrganizationSchema],
    tags=[APITag.documented, APITag.featured],
)
async def list(
    auth_subject: auth.OrganizationsRead,
    pagination: PaginationParamsQuery,
    sorting: sorting.ListSorting,
    slug: str | None = Query(None, description="Filter by slug."),
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[OrganizationSchema]:
    """List organizations."""
    results, count = await organization_service.list(
        session,
        auth_subject,
        slug=slug,
        pagination=pagination,
        sorting=sorting,
    )

    return ListResource.from_paginated_results(
        [OrganizationSchema.model_validate(result) for result in results],
        count,
        pagination,
    )


@router.get(
    "/{id}",
    summary="Get Organization",
    response_model=OrganizationSchema,
    responses={404: OrganizationNotFound},
    tags=[APITag.documented, APITag.featured],
)
async def get(
    id: OrganizationID,
    auth_subject: auth.OrganizationsRead,
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    """Get an organization by ID."""
    organization = await organization_service.get_by_id(session, auth_subject, id)

    if organization is None:
        raise ResourceNotFound()

    return organization


@router.post(
    "/",
    response_model=OrganizationSchema,
    status_code=201,
    summary="Create Organization",
    responses={201: {"description": "Organization created."}},
    tags=[APITag.documented, APITag.featured],
)
async def create(
    organization_create: OrganizationCreate,
    auth_subject: auth.OrganizationsCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    """Create an organization."""
    return await organization_service.create(session, organization_create, auth_subject)


@router.patch(
    "/{id}",
    response_model=OrganizationSchema,
    summary="Update Organization",
    responses={
        200: {"description": "Organization updated."},
        403: {
            "description": "You don't have the permission to update this organization.",
            "model": NotPermitted.schema(),
        },
        404: OrganizationNotFound,
    },
    tags=[APITag.documented, APITag.featured],
)
async def update(
    id: OrganizationID,
    organization_update: OrganizationUpdate,
    auth_subject: auth.OrganizationsWrite,
    authz: Authz = Depends(Authz.authz),
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    """Update an organization."""
    organization = await organization_service.get_by_id(session, auth_subject, id)

    if organization is None:
        raise ResourceNotFound()

    if not await authz.can(auth_subject.subject, AccessType.write, organization):
        raise NotPermitted()

    return await organization_service.update(
        session, authz, organization, organization_update, auth_subject
    )


@router.get(
    "/{id}/account",
    response_model=AccountSchema,
    summary="Get Organization Account",
    responses={
        403: {
            "description": "You don't have the permission to update this organization.",
            "model": NotPermitted.schema(),
        },
        404: {
            "description": "Organization not found or account not set.",
            "model": ResourceNotFound.schema(),
        },
    },
    tags=[APITag.private],
)
async def get_account(
    id: OrganizationID,
    auth_subject: auth.OrganizationsWrite,
    authz: Authz = Depends(Authz.authz),
    session: AsyncSession = Depends(get_db_session),
) -> Account:
    """Get the account for an organization."""
    organization = await organization_service.get_by_id(session, auth_subject, id)

    if organization is None:
        raise ResourceNotFound()

    if not await authz.can(auth_subject.subject, AccessType.write, organization):
        raise NotPermitted()

    if organization.account_id is None:
        raise ResourceNotFound()

    account = await account_service.get_by_id(session, organization.account_id)

    if account is None:
        raise ResourceNotFound()

    return account


@router.patch(
    "/{id}/account",
    response_model=OrganizationSchema,
    summary="Set Organization Account",
    responses={
        200: {"description": "Organization account set."},
        403: {
            "description": "You don't have the permission to update this organization.",
            "model": NotPermitted.schema(),
        },
        404: OrganizationNotFound,
    },
    tags=[APITag.private],
)
async def set_account(
    id: OrganizationID,
    set_account: OrganizationSetAccount,
    auth_subject: auth.OrganizationsWrite,
    authz: Authz = Depends(Authz.authz),
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    """Set the account for an organization."""
    organization = await organization_service.get_by_id(session, auth_subject, id)

    if organization is None:
        raise ResourceNotFound()

    if not await authz.can(auth_subject.subject, AccessType.write, organization):
        raise NotPermitted()

    return await organization_service.set_account(
        session,
        authz=authz,
        auth_subject=auth_subject,
        organization=organization,
        account_id=set_account.account_id,
    )


@router.get(
    "/{id}/members",
    response_model=ListResource[OrganizationMember],
    tags=[APITag.private],
)
async def members(
    auth_subject: auth.OrganizationsWrite,
    id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[OrganizationMember]:
    """List members in an organization."""
    if not id:
        raise ResourceNotFound()

    org = await organization_service.get(session, id)
    if not org:
        raise ResourceNotFound()

    # if user is member
    self_member = await user_organization_service.get_by_user_and_org(
        session, auth_subject.subject.id, id
    )
    if not self_member:
        raise Unauthorized()

    members = await user_organization_service.list_by_org(session, id)

    return ListResource(
        items=[OrganizationMember.model_validate(m) for m in members],
        pagination=Pagination(total_count=len(members), max_page=1),
    )
