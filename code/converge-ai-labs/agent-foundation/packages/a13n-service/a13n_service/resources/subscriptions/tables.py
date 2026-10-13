"""A subscription selects lifecycle kinds; each matching transition copies it into an outbox row."""

from typing import ClassVar

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from a13n_service.infra.db import Base, Stamped, identity_guarded, rules


class SubscriptionRow(Stamped, Base):
    __tablename__ = "subscriptions"
    KIND: ClassVar[str] = "subscription"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ForeignKeyConstraint(["organization_id", "workspace_id"], ["workspaces.organization_id", "workspaces.id"]),
        Index("ix_subscriptions_workspace_enabled", "workspace_id", "enabled"),
        CheckConstraint("jsonb_typeof(kinds) = 'array' AND jsonb_array_length(kinds) > 0", name="kinds"),
        rules(identity_guarded("subscriptions")),
    )
    id: Mapped[str] = mapped_column(String(72), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    workspace_id: Mapped[str]
    name: Mapped[str]
    url: Mapped[str]
    # Encrypted envelope bound to this row; outbox rows re-encrypt it for their own identity.
    signing_secret: Mapped[dict] = mapped_column(JSONB)
    kinds: Mapped[list] = mapped_column(JSONB)
    # Optional narrowing: {"agent_id", "session_id", "thread_id"}; absent keys match everything.
    filter: Mapped[dict] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("principals.id"))
    updated_by_id: Mapped[str] = mapped_column(ForeignKey("principals.id"))
