from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa

from api.v1.checks import enums
from database import Base  # type: ignore
from sdk.models import AuditMixin
from sdk.models import UUIDModelMixin


class Check(UUIDModelMixin, AuditMixin, Base):
    """Check model"""

    __tablename__ = 'checks'
    user = sa.Column(
        UUID,
        sa.ForeignKey('users.uuid', ondelete='CASCADE'),
    )


class Product(UUIDModelMixin, AuditMixin, Base):
    """Product model"""

    __tablename__ = 'products'

    name = sa.Column(sa.String, nullable=False)
    price = sa.Column(sa.Float, nullable=False)
    quantity = sa.Column(sa.Float, nullable=False, default=1.0)
    check = sa.Column(
        UUID,
        sa.ForeignKey('checks.uuid', ondelete='CASCADE'),
    )


class Payment(UUIDModelMixin, AuditMixin, Base):
    """Payment model"""

    __tablename__ = 'payments'

    type = sa.Column(sa.Enum(enums.PaymentType), nullable=False)
    amount = sa.Column(sa.Float, nullable=False)
    check = sa.Column(
        UUID,
        sa.ForeignKey('checks.uuid', ondelete='CASCADE'),
    )
