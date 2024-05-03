import pytest
from api.v1.auth.schemas import Session
from api.v1.users.schemas import UserCreateInDbWithUUID
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sdk.responses import DefaultResponseSchema
from sdk.responses import ResponseStatus
from tests.public.v1.common import TestBase
from tests.utils import MockCacheBackend


@pytest.mark.asyncio
class TestAuthorizationViews(TestBase):
    async def test_login(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        password = 'password123'
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        response = await client.post(
            app.url_path_for('auth:login'),
            json={
                "email": fake_user.email,
                "password": password
            },
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)

    async def test_wrong_login(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_user: UserCreateInDbWithUUID,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        correct_pass = 'password123'
        wrong_pass = 'pass123456'
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        response = await client.post(
            app.url_path_for('auth:login'),
            json={
                "email": fake_user.email,
                "password": wrong_pass
            },
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.INCORRECT_PASSWORD
        assert DefaultResponseSchema(**json_data)
        response = await client.post(
            app.url_path_for('auth:login'),
            json={
                "email": 'some@gmail.com',
                "password": correct_pass
            },
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.USER_NOT_FOUND
        assert DefaultResponseSchema(**json_data)

    async def test_register(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_client: UserCreateInDbWithUUID,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        password = 'password123'
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        response = await client.post(
            app.url_path_for('auth:register'),
            json={
                "name": fake_client.name,
                "email": fake_client.email,
                "password": password
            },
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)

    async def test_register_user_already_exists(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_client: UserCreateInDbWithUUID,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        password = 'password123'
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        await client.post(
            app.url_path_for('auth:register'),
            json={
                "name": fake_client.name,
                "email": fake_client.email,
                "password": password
            },
        )
        response = await client.post(
            app.url_path_for('auth:register'),
            json={
                "name": fake_client.name,
                "email": fake_client.email,
                "password": password
            },
        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.USER_ALREADY_EXISTS
        assert DefaultResponseSchema(**json_data)

    async def test_refresh_token(
            self,
            app: FastAPI,
            client: AsyncClient,
            fake_session: Session,
            redis: MockCacheBackend,
            mocker: MockerFixture,
    ) -> None:
        mocker.patch('cache.RedisBackend.create_pool', return_value=redis)
        response = await client.post(
            app.url_path_for('auth:refresh-token'),
            json={
                "refresh_token": fake_session.refresh_token,
            },
            headers={'Authorization': f'Bearer {fake_session.access_token}'},

        )
        json_data = response.json()
        assert json_data['custom_code'] == ResponseStatus.OK
        assert DefaultResponseSchema(**json_data)
