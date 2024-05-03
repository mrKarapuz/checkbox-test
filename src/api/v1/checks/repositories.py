import json
from datetime import datetime
from typing import Type, Optional
from uuid import UUID
from api.v1.checks import enums
from api.v1.checks.models import Check
from api.v1.checks.models import Product
from api.v1.checks.models import Payment
from api.v1.checks.schemas import CheckSchema
from api.v1.checks.schemas import ProductSchema
from api.v1.checks.schemas import PaymentCreate
from database import database
from sdk.exceptions.exceptions import make_error
from sdk.ordering import OrderingManager
from sdk.pagination import PaginationManager
from sdk.repositories import BaseRepository
from sdk.responses import ResponseStatus
from sdk.schemas import PaginatedSchema
from sqlalchemy import select
from sqlalchemy import func
import sqlalchemy as sa


class CheckRepository(BaseRepository):
    model: Check = Check

    @classmethod
    async def get_checks(
            cls: Type['CheckRepository'],
            created_at_before: Optional[datetime],
            created_at_after: Optional[datetime],
            total_gte: Optional[int],
            total_lte: Optional[int],
            payment_type: Optional[enums.PaymentType],
            ordering: OrderingManager,
            pagination: PaginationManager,
            user_uuid: UUID,
            search_query: Optional[str] = None,
    ) -> PaginatedSchema[CheckSchema]:
        checks_table = Check.__table__
        products_table = Product.__table__
        payments_table = Payment.__table__
        total = func.sum(products_table.c.price * products_table.c.quantity)
        rest = (func.coalesce(payments_table.c.amount, 0) - func.sum(
            products_table.c.price * products_table.c.quantity))
        query = (
            select([
                cls.model.uuid.label('uuid'),
                cls.model.created_at,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        sa.text("'name', products.name"),
                        sa.text("'price', products.price"),
                        sa.text("'quantity', products.quantity"),
                        sa.text("'total', products.price * products.quantity"),
                    )
                ).label('products'),
                func.jsonb_build_object(
                    sa.text("'amount', payments.amount"),
                    sa.text("'type', payments.type"),
                ).label('payment'),
                total.label('total'),
                rest.label('rest')
            ])
            .select_from(
                checks_table
                .outerjoin(products_table, products_table.c.check == checks_table.c.uuid)
                .outerjoin(payments_table, payments_table.c.check == checks_table.c.uuid)
            )
        ).where(
            cls.model.user == user_uuid
        )
        if search_query:
            query = query.filter(products_table.c.name.ilike(f"%{search_query}%"))
        if created_at_before:
            query = query.where(cls.model.created_at <= created_at_before)
        if created_at_after:
            query = query.where(cls.model.created_at >= created_at_after)
        if total_gte:
            query = query.having(total >= total_gte)
        if total_lte:
            query = query.having(total <= total_lte)
        if payment_type:
            query = query.where(Payment.type == payment_type)
        order_fields = ordering.get_fields(cls.model, additional_fields={
            'total': total,
            'rest': rest,
        })
        query = query.group_by(checks_table.c.uuid, payments_table.c.amount, payments_table.c.type).order_by(
            *order_fields)
        total_count = await database.fetch_val(
            sa.select([sa.func.count()]).select_from(query.alias('original_query')),
        )
        pagination.check_page(total_count)
        paginated_query = query.limit(pagination.page_size).offset(
            pagination.page * pagination.page_size,
        )
        raw_results = await database.fetch_all(paginated_query)
        results = [CheckSchema(
            uuid=obj['uuid'],
            created_at=obj['created_at'],
            products=[ProductSchema(**product) for product in json.loads(obj['products'])],
            payment=PaymentCreate(**json.loads(obj['payment']))
        ) for obj in raw_results]
        _next = pagination.get_next_page(total_count)
        _prev = pagination.get_prev_page()
        _page_count = pagination.get_page_count(total_count)
        return PaginatedSchema(
            total_count=total_count,
            page_count=_page_count,
            next=_next,
            previous=_prev,
            results=results,
        )

    @classmethod
    async def get_check(
            cls: Type['CheckRepository'],
            check_uuid: UUID,
            user_uuid: Optional[UUID] = None,
    ) -> CheckSchema:
        checks_table = Check.__table__
        products_table = Product.__table__
        payments_table = Payment.__table__
        query = (
            select([
                cls.model.uuid.label('uuid'),
                cls.model.created_at,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        sa.text("'name', products.name"),
                        sa.text("'price', products.price"),
                        sa.text("'quantity', products.quantity"),
                    )
                ).label('products'),
                func.jsonb_build_object(
                    sa.text("'amount', payments.amount"),
                    sa.text("'type', payments.type"),
                ).label('payment'),
            ])
            .select_from(
                checks_table
                .outerjoin(products_table, products_table.c.check == checks_table.c.uuid)
                .outerjoin(payments_table, payments_table.c.check == checks_table.c.uuid)
            )
        ).where(
            cls.model.uuid == check_uuid
        ).group_by(
            checks_table.c.uuid, payments_table.c.amount, payments_table.c.type
        )
        if user_uuid:
            query = query.where(cls.model.user == user_uuid)
        raw_result = await database.fetch_one(query)
        if raw_result is None:
            raise make_error(
                custom_code=ResponseStatus.CHECK_NOT_FOUND,
                message='Check not found',
            )
        return CheckSchema(
            uuid=raw_result['uuid'],
            created_at=raw_result['created_at'],
            products=[ProductSchema(**product) for product in json.loads(raw_result['products'])],
            payment=PaymentCreate(**json.loads(raw_result['payment']))
        )


class ProductRepository(BaseRepository):
    model: Product = Product


class PaymentRepository(BaseRepository):
    model: Payment = Payment
