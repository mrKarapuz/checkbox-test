from uuid import UUID
from api.v1.checks import enums
from sdk.exceptions.exceptions import make_error
from sdk.responses import ResponseStatus
from sdk.schemas import BaseSchema
from sdk.schemas import UUIDSchemaMixin
from sdk.schemas import AuditSchemaMixin
from pydantic import root_validator
from pydantic import validator
from pydantic import confloat
from typing import List
from typing import Optional


class PaymentCreate(BaseSchema):
    type: enums.PaymentType = enums.PaymentType.CASH
    amount: float


class PaymentInDb(UUIDSchemaMixin, PaymentCreate):
    check: UUID


class ProductCreate(BaseSchema):
    name: str
    price: float
    quantity: confloat(gt=0)


class ProductInDb(UUIDSchemaMixin, ProductCreate):
    check: UUID


class ProductSchema(ProductCreate):
    total: float

    @root_validator(pre=True)
    def calculate_total(
            cls,  # noqa
            values
    ):
        price = values.get('price')
        quantity = values.get('quantity')
        if price is not None and quantity is not None and not values.get('total'):
            values['total'] = float(price * quantity)
        return values


class CheckCreate(BaseSchema):
    products: List[ProductCreate]
    payment: PaymentCreate

    @validator('products')
    def check_products_not_empty(cls, v):  # noqa
        if not v:
            raise make_error(
                custom_code=ResponseStatus.PRODUCT_LIST_CANNOT_BE_EMPTY,
                message='The product list cannot be empty',
            )
        return v


class CheckCreateInDb(UUIDSchemaMixin):
    user: UUID


class CheckSchema(UUIDSchemaMixin, AuditSchemaMixin):
    products: List[ProductSchema]
    payment: PaymentCreate
    total: Optional[float] = 0
    rest: Optional[float] = 0

    @root_validator(pre=True)
    def calculate_total(
            cls,  # noqa
            values
    ):
        if not values.get('total'):
            values['total'] = sum(product.total for product in values.get('products', []))
        if not values.get('rest'):
            values['rest'] = values['payment'].amount - values['total']
        if values['rest'] < 0:
            raise make_error(
                custom_code=ResponseStatus.NOT_ENOUGH_MONEY,
                message='Not enough money',
            )
        if values['total'] < 1:
            raise make_error(
                custom_code=ResponseStatus.EMPTY_CHECK,
                message='Check is empty',
            )
        return values
