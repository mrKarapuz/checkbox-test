import sqlalchemy as sa
from database import Base  # type: ignore

from sdk.models import AuditMixin
from sdk.models import UUIDModelMixin


class User(UUIDModelMixin, AuditMixin, Base):
    """User model"""

    __tablename__ = 'users'

    name = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, nullable=True)
    hashed_password = sa.Column(sa.String, nullable=True)
