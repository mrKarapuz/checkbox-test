import datetime
import uuid
from typing import Type
from typing import List
from uuid import UUID
from api.v1.checks import enums
from api.v1.checks.schemas import CheckCreate
from api.v1.checks.schemas import CheckSchema
from api.v1.checks.schemas import PaymentCreate
from api.v1.checks.schemas import PaymentInDb
from api.v1.checks.schemas import ProductInDb
from api.v1.checks.schemas import ProductCreate
from api.v1.checks.schemas import ProductSchema
from api.v1.checks.repositories import CheckRepository
from api.v1.checks.repositories import ProductRepository
from api.v1.checks.repositories import PaymentRepository
from config import settings


class ProductService:
    repository = ProductRepository

    @classmethod
    async def create_products(
            cls,
            check_uuid: UUID,
            products: List[ProductCreate]
    ) -> List[ProductSchema]:
        products = [ProductInDb(
            uuid=uuid.uuid4(),
            check=check_uuid,
            **product.dict()
        ).dict() for product in products]
        await cls.repository.create(items=products).execute()
        return [ProductSchema(**product) for product in products]


class PaymentService:
    repository = PaymentRepository

    @classmethod
    async def create_payment(
            cls,
            check_uuid: UUID,
            payment: PaymentCreate
    ) -> None:
        payment = PaymentInDb(**payment.dict(), check=check_uuid, uuid=uuid.uuid4())
        await cls.repository.create(**payment.dict()).execute()


class CheckService:
    repository = CheckRepository

    @classmethod
    async def create_check(
            cls: Type['CheckService'],
            check_data: CheckCreate,
            user_id: UUID
    ) -> CheckSchema:
        check_uuid = uuid.uuid4()
        await cls.repository.create(
            uuid=check_uuid,
            user=user_id
        ).execute()
        products = await ProductService.create_products(check_uuid, check_data.products)
        await PaymentService.create_payment(check_uuid, check_data.payment)
        return CheckSchema(
            uuid=check_uuid,
            created_at=datetime.datetime.now(),
            products=products,
            payment=check_data.payment,
        )

    @staticmethod
    def generate_check_text(check_data: CheckSchema) -> str:
        lines = list()
        lines.append(settings.CHECK_HEADER.center(settings.CHECK_LENGTH))
        lines.append('=' * settings.CHECK_LENGTH)
        lines.append('')
        for product in check_data.products:
            quantity_price = f'{product.quantity:.2f} x {product.price:.2f}'
            lines.append(quantity_price)
            name_parts = []
            product_name = product.name
            while len(product_name) > 0:
                if len(product_name) <= settings.CHECK_LENGTH - 10:
                    name_parts.append(product_name)
                    break
                else:
                    space_index = product_name[:30].rfind(' ')
                    if space_index == -1:
                        space_index = settings.CHECK_LENGTH - 10
                    name_parts.append(product_name[:space_index])
                    product_name = product_name[space_index:].lstrip()
            for i, part in enumerate(name_parts):
                if i < len(name_parts) - 1:
                    lines.append(f'    {part}')
                else:
                    total_space = settings.CHECK_LENGTH - len(part) - 4
                    lines.append(f'    {part}' + f'{product.total:.2f}'.rjust(total_space, '.'))
        lines.append('')
        lines.append('-' * settings.CHECK_LENGTH)
        lines.append('СУМА'.ljust(settings.CHECK_LENGTH - 10) + f'{check_data.total:.2f}'.rjust(10))
        payment_type = 'Картка' if check_data.payment.type == enums.PaymentType.CASHLESS else 'Готівка'
        lines.append(payment_type.ljust(settings.CHECK_LENGTH - 10) + f'{check_data.payment.amount:.2f}'.rjust(10))
        lines.append('Решта'.ljust(settings.CHECK_LENGTH - 10) + f'{check_data.rest:.2f}'.rjust(10))
        lines.append('=' * settings.CHECK_LENGTH)
        lines.append(f'{check_data.created_at.strftime("%d.%m.%Y %H:%M")}'.center(settings.CHECK_LENGTH))
        lines.append(settings.CHECK_FOOTER.center(settings.CHECK_LENGTH))
        return '\n'.join(lines)
