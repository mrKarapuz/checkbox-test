from datetime import datetime
from datetime import timedelta
from pydantic import EmailStr
from pydantic import constr
from config import settings
from sdk.schemas import BaseSchema


class Session(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: datetime
    token_type: str = 'bearer'

    @staticmethod
    def get_access_token_expires() -> datetime:
        return datetime.now() + timedelta(minutes=settings.AUTH_JWT_ACCESS_TOKEN_EXP_DELTA_MINUTES)

    @staticmethod
    def get_refresh_token_expires() -> datetime:
        return datetime.now() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXP_DELTA_MINUTES)


class AuthorizationBase(BaseSchema):
    email: EmailStr
    password: constr(strip_whitespace=True, min_length=8, max_length=20) = None
