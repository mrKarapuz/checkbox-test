from cache import RedisBackend
from dependencies import cache_storage
from dependencies import get_access_token
from dependencies import get_authenticated_user
from dependencies import get_tracking_data
from dependencies import get_transaction
from fastapi import Body
from fastapi import Depends
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from transaction import Transaction
from api.v1.auth.schemas import Session
from api.v1.auth.schemas import AuthorizationBase
from api.v1.auth.services import AuthorizationService
from api.v1.auth.services import SessionService
from api.v1.users.schemas import UserCreate
from api.v1.users.services import UserService
from sdk.exceptions.exceptions import make_error
from sdk.responses import DefaultResponse
from sdk.responses import ResponseStatus
from sdk.responses import DefaultResponseSchema
from sdk.schemas import TrackingSchemaMixin

router = InferringRouter()


@cbv(router)
class AuthorizationViews:
    tracking_params: TrackingSchemaMixin = Depends(get_tracking_data)

    @router.post(
        '/register',
        name='auth:register',
        response_model=DefaultResponseSchema[Session]
    )
    async def register(
        self,
        *,
        transaction: Transaction = Depends(get_transaction),
        redis: RedisBackend = Depends(cache_storage),
        user_data: UserCreate,
    ) -> DefaultResponse:
        async with transaction:
            user = await AuthorizationService.register(
                user_data,
            )
            session = await SessionService.create_session(
                redis,
                user,
            )
        return DefaultResponse(content=session)

    @router.post(
        '/login',
        name='auth:login',
        response_model=DefaultResponseSchema[bool]
    )
    async def login(
        self,
        *,
        redis: RedisBackend = Depends(cache_storage),
        user_data: AuthorizationBase,
    ) -> DefaultResponse:
        user = await UserService.get_user_with_password_hash(email=user_data.email)
        is_verified = AuthorizationService.verify_password(user_data.password, user.hashed_password)
        if not is_verified:
            raise make_error(
                custom_code=ResponseStatus.INCORRECT_PASSWORD,
                message='Incorrect password',
            )
        session = await SessionService.create_session(
            redis,
            user,
        )
        return DefaultResponse(content=session)

    @router.post(
        '/refresh-token',
        name='auth:refresh-token',
        response_model=DefaultResponseSchema[Session],
        dependencies=[Depends(get_authenticated_user)],
    )
    async def refresh_token(
        self,
        *,
        redis: RedisBackend = Depends(cache_storage),
        transaction: Transaction = Depends(get_transaction),
        access_token: str = Depends(get_access_token),
        refresh_token: str = Body(..., embed=True),
    ) -> DefaultResponse:
        async with transaction:
            session = await SessionService.refresh_session(
                access_token=access_token,
                refresh_token=refresh_token,
                redis=redis,
            )
            return DefaultResponse(content=session)

    @router.delete(
        '/logout',
        name='auth:logout',
        response_model=DefaultResponseSchema,
        dependencies=[Depends(get_authenticated_user)],
    )
    async def logout(
        self,
        *,
        redis: RedisBackend = Depends(cache_storage),
        access_token: str = Depends(get_access_token),
    ) -> DefaultResponse:
        await SessionService.logout(access_token, redis)
        return DefaultResponse()
