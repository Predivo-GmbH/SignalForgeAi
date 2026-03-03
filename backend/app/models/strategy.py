import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Strategy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BrokerConnection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "broker_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    broker: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    api_secret_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
