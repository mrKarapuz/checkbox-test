import uuid
import jwt
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional
from cache import RedisBackend
from config import settings
from api.v1.auth.schemas import Session
from api.v1.users.schemas import User
from api.v1.users.schemas import UserCreateInDb
from api.v1.users.schemas import UserCreate
from api.v1.users.services import UserService
from sdk.exceptions.exceptions import make_error
from sdk.responses import ResponseStatus
from sdk.utils import DefaultJSONEncoder
from passlib.context import CryptContext

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenService:
    @classmethod
    def create_access(
            cls,
            payload: Dict[str, Any],
            secret_key: str,
            sub: str,
            expires_in: datetime,
            algorithm: str,
    ) -> str:
        body = {
            'iat': datetime.utcnow(),
            'exp': expires_in,
            'sub': sub,
            'data': payload,
        }
        return jwt.encode(
            payload=body,
            key=secret_key,
            algorithm=algorithm,
            json_encoder=DefaultJSONEncoder,
        )

    @classmethod
    def create_refresh(
            cls,
            secret_key: str,
            sub: str,
            expires_in: datetime,
            algorithm: str,
    ) -> str:
        body = {
            'iat': datetime.utcnow(),
            'exp': expires_in,
            'sub': sub,
        }
        return jwt.encode(
            payload=body,
            key=secret_key,
            algorithm=algorithm,
            json_encoder=DefaultJSONEncoder,
        )

    @classmethod
    def get_payload(
            cls,
            token: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.AUTH_JWT_ALGORITHM])
        except jwt.PyJWTError:
            return None


class SessionService:
    user_schema: User = User

    @classmethod
    async def create_session(
            cls,
            redis: RedisBackend,
            user: user_schema,
    ) -> Session:
        expires_in = Session.get_access_token_expires()
        access_token = TokenService.create_access(
            payload=user.dict(),
            secret_key=settings.SECRET_KEY,
            sub=str(user.uuid),
            expires_in=expires_in,
            algorithm=settings.AUTH_JWT_ALGORITHM,
        )
        refresh_token = TokenService.create_refresh(
            secret_key=settings.SECRET_KEY,
            sub=str(user.uuid),
            expires_in=Session.get_refresh_token_expires(),
            algorithm=settings.AUTH_JWT_ALGORITHM,
        )
        await redis.set(
            f'{refresh_token}:{access_token}:{user.uuid}',
            str(user.uuid),
            expire=settings.JWT_REFRESH_TOKEN_EXP_DELTA_MINUTES,
        )
        return Session(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    @classmethod
    async def logout(cls, access_token: str, redis: RedisBackend) -> None:
        payload = TokenService.get_payload(access_token)
        expires_in = payload['exp'] if payload else 0
        await redis.set(
            f'bl:{access_token}',
            access_token,
            expire=expires_in,
        )

    @classmethod
    async def logout_all(
            cls,
            user_id: uuid.UUID,
            redis: RedisBackend,
    ) -> None:
        key = f'*:*:{user_id}'
        keys = await redis.keys(key)
        expire = (datetime.now() - Session.get_access_token_expires()).seconds
        for key in keys:
            access_token = key.decode('utf-8').split(':')[2]
            await redis.set(
                f'bl:{access_token}',
                access_token,
                expire=expire,
            )

    @classmethod
    async def refresh_session(
            cls,
            redis: RedisBackend,
            access_token: str,
            refresh_token: str,
    ) -> Session:
        token_invalid = make_error(
            custom_code=ResponseStatus.INVALID_ACCESS_OR_REFRESH_TOKEN,
            message='Token invalid or expired',
        )
        refresh_payload = TokenService.get_payload(refresh_token)
        if refresh_payload is None:
            raise token_invalid
        user_id = refresh_payload.get('sub')
        if user_id is None:
            raise token_invalid
        user = await UserService.get_user(uuid=user_id)
        in_blacklist = await redis.get(f'bl:{access_token}')
        if in_blacklist:
            raise token_invalid
        session = await redis.get(f'{refresh_token}:{access_token}:{user_id}')
        if session is None:
            raise token_invalid
        await cls.logout(access_token, redis)
        return await cls.create_session(user=user, redis=redis)


class AuthorizationService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        return PWD_CONTEXT.hash(password + settings.SECRET_KEY)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return PWD_CONTEXT.verify(plain_password + settings.SECRET_KEY, hashed_password)

    @classmethod
    async def register(
            cls,
            user: UserCreate,
    ) -> User:
        user_in_db = UserCreateInDb(
            email=user.email,
            name=user.name,
            hashed_password=cls.get_password_hash(user.password)
        )
        return await UserService.create_user(user_data=user_in_db)
