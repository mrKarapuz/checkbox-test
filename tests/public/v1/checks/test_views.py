import datetime
import uuid
from typing import List
import pytest
from api.v1.auth.schemas import Session
from api.v1.checks import enums
from api.v1.checks.schemas import CheckCreateInDb
from api.v1.checks.schemas import ProductInDb
from api.v1.checks.schemas import PaymentInDb
from api.v1.checks.services import CheckService, ProductService, PaymentService
from api.v1.users.schemas import UserCreateInDbWithUUID
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_mock import MockerFixture
from api.v1.users.services import UserService
from sdk.responses import DefaultResponseSchema
from sdk.responses import ResponseStatus
from tests.public.v1.common import TestBase
from tests.utils import MockCacheBackend


@pytest.mark.asyncio
class TestChecksViews(TestBase):
    async def test_check_create(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        products_as_dicts = [
            {
                'name': product.name,
                'price': product.price,
                'quantity': product.quantity,
            } for product in fake_products
        ]
        fake_payment_as_dict = {
            'type': fake_payment.type,
            'amount': fake_payment.amount,
        }
        response = await client.post(
            app.url_path_for('check:create'),
            json={
                'products': products_as_dicts,
                'payment': fake_payment_as_dict
            },
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)

    async def test_check_create_product_cannot_be_empty(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        fake_payment_as_dict = {
            'type': fake_payment.type,
            'amount': fake_payment.amount,
        }
        response = await client.post(
            app.url_path_for('check:create'),
            json={
                'products': [],
                'payment': fake_payment_as_dict
            },
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.PRODUCT_LIST_CANNOT_BE_EMPTY
        assert DefaultResponseSchema(**json_data)

    async def test_check_create_payment_amount_not_enough(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        products_as_dicts = [
            {
                'name': product.name,
                'price': product.price,
                'quantity': product.quantity,
            } for product in fake_products
        ]
        response = await client.post(
            app.url_path_for('check:create'),
            json={
                'products': products_as_dicts,
                'payment': {
                    'type': fake_payment.type,
                    'amount': 100
                }
            },
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.NOT_ENOUGH_MONEY
        assert DefaultResponseSchema(**json_data)

    async def test_check_create_total_empty(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        products_as_dicts = [
            {
                'name': product.name,
                'price': 0,
                'quantity': product.quantity,
            } for product in fake_products
        ]
        response = await client.post(
            app.url_path_for('check:create'),
            json={
                'products': products_as_dicts,
                'payment': {
                    'type': fake_payment.type,
                    'amount': 100
                }
            },
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.EMPTY_CHECK
        assert DefaultResponseSchema(**json_data)

    async def test_check_all(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        response = await client.get(
            app.url_path_for('checks:all'),
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)
        assert len(json_data['data']['results']) == 1

    async def test_check_all_with_filters(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        second_check_uuid = str(uuid.uuid4())
        filter_created_at = datetime.datetime(year=2024, month=1, day=5)
        utc_zone = datetime.timezone(datetime.timedelta(hours=0))
        filter_created_at = filter_created_at.replace(tzinfo=utc_zone)
        await CheckService.repository.create(
            **{
                'uuid': second_check_uuid,
                'user': str(fake_user.uuid),
                'created_at': filter_created_at
            }
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await ProductService.repository.create(items=[
            {
                'uuid': 'fdc4a1b2-0333-4cb5-97c6-5a9995fb2864',
                'name': 'chair',
                'price': 324.3,
                'quantity': 2,
                'check': second_check_uuid,
            },
            {
                'uuid': '3279f47c-e018-44bd-b850-ef272bd8fce6',
                'name': 'fridge',
                'price': 234.3,
                'quantity': 1,
                'check': second_check_uuid
            },
        ]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        await PaymentService.repository.create(**{
            'uuid': '116eca4b-6834-43c7-a5d5-a8ad92db176b',
            'type': enums.PaymentType.CASHLESS,
            'amount': 1000,
            'check': second_check_uuid
        }).execute()
        response = await client.get(
            app.url_path_for('checks:all'),
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)
        assert len(json_data['data']['results']) == 2

        # Search test
        search_row = 'chair'
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'search': search_row},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            assert search_row in [product.get('name') for product in check.get('products')]

        # created_at_before test
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'created_at_before': filter_created_at.isoformat()},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            created_at = datetime.datetime.strptime(check.get('created_at'), date_format)
            assert created_at <= filter_created_at

        # created_at_before test
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'created_at_after': filter_created_at.isoformat()},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            created_at = datetime.datetime.strptime(check.get('created_at'), date_format)
            assert created_at >= filter_created_at

        # total_gte test
        total_gte = 500
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'total_gte': total_gte},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            assert check.get('total') >= total_gte

        # total_gte test
        total_lte = 500
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'total_lte': total_lte},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            assert check.get('total') <= total_lte

        # payment_type test
        payment_type = enums.PaymentType.CASH
        response = await client.get(
            app.url_path_for('checks:all'),
            params={'payment_type': payment_type.value},
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        checks = json_data['data']['results']
        for check in checks:
            assert check.get('payment').get('type') == payment_type

    async def test_check_get(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        response = await client.get(
            app.url_path_for('checks:get', check_uuid=fake_check.uuid),
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)
        assert json_data['data']['uuid'] == str(fake_check.uuid)

    async def test_check_get_wrong_uuid(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        response = await client.get(
            app.url_path_for('checks:get', check_uuid='55791d38-18a0-47b7-a806-2be7375dfcd3'),
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.CHECK_NOT_FOUND
        assert DefaultResponseSchema(**json_data)

    async def test_client_check_get(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_session: Session,
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        response = await client.get(
            app.url_path_for('client:checks:get', check_uuid=fake_check.uuid),
            headers={'Authorization': f'Bearer {fake_session.access_token}'},
        )
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
        assert isinstance(response.text, str)
        assert response.status_code == 200

    async def test_client_check_get_without_auth(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,  # noqa
            fake_check: CheckCreateInDb,
            fake_products: List[ProductInDb],
            fake_payment: PaymentInDb,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await CheckService.repository.create(
            **fake_check.dict()
        ).execute()
        await ProductService.repository.create(items=[fake_product.dict() for fake_product in fake_products]).execute()
        await PaymentService.repository.create(**fake_payment.dict()).execute()
        response = await client.get(
            app.url_path_for('client:checks:get', check_uuid=fake_check.uuid),
        )
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
        assert isinstance(response.text, str)
        assert response.status_code == 200
