from datetime import datetime
from typing import Optional
from uuid import UUID
from starlette.responses import PlainTextResponse
from api.v1.checks.schemas import CheckCreate
from api.v1.checks.schemas import CheckSchema
from api.v1.checks.services import CheckService
from api.v1.users.schemas import User
from dependencies import get_transaction
from dependencies import get_authenticated_user
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Depends
from fastapi_utils.cbv import cbv
from api.v1.checks import enums
from transaction import Transaction
from sdk.ordering import OrderingManager
from sdk.ordering import get_ordering
from sdk.pagination import PaginationManager
from sdk.responses import DefaultResponse
from sdk.responses import DefaultResponseSchema
from sdk.schemas import PaginatedSchema

router = APIRouter()


@cbv(router)
class CheckViews:
    authenticated_user: User = Depends(get_authenticated_user)

    @router.post(
        '/',
        name='check:create',
        response_model=DefaultResponseSchema[CheckSchema],
    )
    async def create_check(
            self,
            check_data: CheckCreate,
            transaction: Transaction = Depends(get_transaction),
    ) -> DefaultResponse:
        async with transaction:
            check = await CheckService.create_check(
                check_data=check_data,
                user_id=self.authenticated_user.uuid
            )
        return DefaultResponse(
            content=check
        )

    @router.get(
        '/',
        name='checks:all',
        response_model=DefaultResponseSchema[PaginatedSchema[CheckSchema]],
    )
    async def get_checks(
            self,
            search_query: Optional[str] = Query(None, alias='search'),
            created_at_before: Optional[datetime] = Query(
                None, alias='created_at_before',
                description='Example: 2024-04-01T00:00:00'
            ),
            created_at_after: Optional[datetime] = Query(
                None, alias='created_at_after',
                description='Example 2024-04-01T00:00:00'
            ),
            total_gte: Optional[int] = Query(None, alias='total_gte'),
            total_lte: Optional[int] = Query(None, alias='total_lte'),
            payment_type: Optional[enums.PaymentType] = Query(None, alias='payment_type'),
            ordering: OrderingManager = Depends(get_ordering),
            pagination: PaginationManager = Depends(PaginationManager),
    ) -> DefaultResponse:
        checks = await CheckService.repository.get_checks(
            created_at_before=created_at_before,
            created_at_after=created_at_after,
            total_gte=total_gte,
            total_lte=total_lte,
            payment_type=payment_type,
            ordering=ordering,
            pagination=pagination,
            search_query=search_query,
            user_uuid=self.authenticated_user.uuid,
        )
        return DefaultResponse(content=checks)

    @router.get(
        '/{check_uuid}',
        name='checks:get',
        response_model=DefaultResponseSchema[CheckSchema],
    )
    async def get_check(
            self,
            *,
            check_uuid: UUID,
    ) -> DefaultResponse:
        check = await CheckService.repository.get_check(
            check_uuid=check_uuid,
            user_uuid=self.authenticated_user.uuid,
        )
        return DefaultResponse(content=check)


@router.get(
    '/client/{check_uuid}',
    name='client:checks:get',
    response_class=PlainTextResponse,
)
async def get_check_for_client(
        *,
        check_uuid: UUID,
) -> PlainTextResponse:
    try:
        check = await CheckService.repository.get_check(check_uuid=check_uuid)
        check_text = CheckService.generate_check_text(check)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(content=check_text)
