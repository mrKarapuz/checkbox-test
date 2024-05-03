import asyncio
from typing import Generator, List

import pytest
import pytest_asyncio
from alembic.command import upgrade as alembic_upgrade
from api.v1.auth.schemas import Session
from api.v1.auth.services import SessionService
from api.v1.checks import enums
from api.v1.users.schemas import UserCreateInDbWithUUID
from api.v1.users.schemas import UserCreateInDb
from api.v1.checks.schemas import CheckCreateInDb
from api.v1.checks.schemas import ProductInDb
from api.v1.checks.schemas import PaymentInDb
from api.v1.users.services import UserService
from config import settings
from database import database
from fastapi import FastAPI
from httpx import AsyncClient
from requests import Session as RequestSession
from sqlalchemy_utils import create_database
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import drop_database
from transaction import Transaction
from tests.utils import alembic_config_from_url, MockCacheBackend
from sdk.schemas import TrackingSchemaMixin

if not settings.TESTING:
    raise ValueError('Please, set TESTING=True in core/config.py to run tests')


@pytest_asyncio.fixture()
async def db_connection() -> Generator:
    if not database_exists(settings.DB_URI):
        create_database(settings.DB_URI)
        alembic_config = alembic_config_from_url(settings.DB_URI)
        alembic_upgrade(alembic_config, 'head')
    if not database.is_connected:
        await database.connect()
    transaction = await database.transaction()
    try:
        yield transaction
    finally:
        await transaction.rollback()


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> Generator[RequestSession, None, None]:
    async with AsyncClient(app=app, base_url='http://localhost') as c:
        yield c


@pytest.fixture(scope='session')
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def app(db_connection: Transaction) -> FastAPI:
    from main import app as fastapi_app

    fastapi_app.router.on_startup = []
    fastapi_app.router.on_shutdown = []

    return fastapi_app


@pytest.fixture()
def tracking_params() -> TrackingSchemaMixin:
    return TrackingSchemaMixin(
        ip='192.168.0.1',
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) '
                   'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1',
    )


@pytest.fixture()
def redis() -> MockCacheBackend:
    return MockCacheBackend()


def pytest_sessionfinish() -> None:
    if database_exists(settings.DB_URI):
        drop_database(settings.DB_URI)


@pytest.fixture()
def fake_client() -> UserCreateInDbWithUUID:
    return UserCreateInDbWithUUID(
        uuid='c0cd852e-1a28-4837-8307-83e3385ba251',
        name='John',
        email='client@example.com',
        hashed_password='$2b$12$NXh.coP0UxBO1mK3O07sAO8gwkLXx.9rFURJuB0wQn4bmD6S1m9sq'
    )


@pytest_asyncio.fixture()
async def fake_user(fake_client: UserCreateInDbWithUUID) -> UserCreateInDbWithUUID:
    await UserService.repository.create(**fake_client.dict()).execute()
    return fake_client


@pytest.fixture()
def fake_check(fake_client: UserCreateInDbWithUUID) -> CheckCreateInDb:
    return CheckCreateInDb(
        uuid='1a5ae7d3-7c2c-4d14-ad3f-c81bf3092831',
        user=str(fake_client.uuid)
    )


@pytest.fixture()
def fake_product(fake_check: CheckCreateInDb) -> ProductInDb:
    return ProductInDb(
        uuid='117aecbb-f430-4076-ac98-dc082bb4a849',
        name='Bread',
        price=10,
        quantity=2,
        check=str(fake_check.uuid)
    )


@pytest.fixture()
def fake_products(fake_check: CheckCreateInDb) -> List[ProductInDb]:
    return [
        ProductInDb(
            uuid='6db47907-14b1-47b8-8262-3d2b7890bad8',
            name='Butter',
            price=13.3,
            quantity=3,
            check=str(fake_check.uuid)
        ),
        ProductInDb(
            uuid='fccee2fd-2429-4487-a8a4-db66efa52965',
            name='Knife',
            price=117,
            quantity=2,
            check=str(fake_check.uuid)
        ),
        ProductInDb(
            uuid='d72a8b0c-ad2d-44c3-98f1-0ebbd86db078',
            name='Milk',
            price=23.8,
            quantity=1,
            check=str(fake_check.uuid)
        )
    ]


@pytest.fixture()
def fake_payment(fake_check: CheckCreateInDb) -> PaymentInDb:
    return PaymentInDb(
        uuid='ff8a1344-2055-4357-9fa9-138f4fc4bf0e',
        type=enums.PaymentType.CASH,
        amount=1000,
        check=fake_check.uuid
    )


@pytest_asyncio.fixture()
async def fake_session(fake_user: UserCreateInDbWithUUID, redis: MockCacheBackend) -> Session:
    return await SessionService.create_session(redis, fake_user)
