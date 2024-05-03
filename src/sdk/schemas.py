from datetime import datetime
from datetime import timezone
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar
from uuid import UUID
from config import settings
from pydantic import BaseModel
from pydantic.generics import GenericModel


class BaseSchema(BaseModel):
    class Config:
        json_encoders = {datetime: lambda dt: dt.strftime(settings.DEFAULT_DATETIME_FORMAT)}


BaseSchemaType = TypeVar('BaseSchemaType', bound=BaseSchema)


class UUIDSchemaMixin(BaseSchema):
    uuid: UUID


class PaginatedSchema(GenericModel, Generic[BaseSchemaType]):
    total_count: int = 0
    page_count: int
    next: Optional[int]  # noqa: VNE003
    previous: Optional[int]
    results: List[BaseSchemaType]


class ExpireSchemaMixin(BaseSchema):
    start_at: datetime
    end_at: datetime

    @property
    def block_pass_time(self) -> int:
        utc_now = datetime.now(timezone.utc)
        return (self.end_at - utc_now).seconds


class SoftDeleteSchemaMixin(BaseSchema):
    deleted_at: Optional[datetime] = None


class TrackingSchemaMixin(BaseSchema):
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditSchemaMixin(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None
