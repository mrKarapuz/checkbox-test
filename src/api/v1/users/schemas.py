
from typing import Optional
from pydantic import EmailStr
from pydantic import constr
from sdk.schemas import BaseSchema
from sdk.schemas import UUIDSchemaMixin


class UserUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(BaseSchema):
    name: str
    password: constr(strip_whitespace=True, min_length=8, max_length=20)
    email: Optional[EmailStr] = None


class UserCreateInDb(BaseSchema):
    name: str
    email: Optional[EmailStr] = None
    hashed_password: str


class UserCreateInDbWithUUID(UserCreateInDb, UUIDSchemaMixin):
    pass


class User(UUIDSchemaMixin):
    name: str
    email: Optional[str] = None
