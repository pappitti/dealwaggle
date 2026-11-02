"""Entities identify things; assertions carry knowledge, provenance and access.

Never serialize ORM objects directly. Entity existence and labels are themselves
sensitive; only expose entities with an assertion visible to the requester.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(UTC)


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(Record, Base):
    __tablename__ = "users"
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)


class Organisation(Record, Base):
    __tablename__ = "organisations"
    name: Mapped[str] = mapped_column(String(200))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    __table_args__ = (CheckConstraint("role IN ('owner', 'member')"),)


class Entity(Record, Base):
    __tablename__ = "entities"
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    __table_args__ = (CheckConstraint("kind IN ('person', 'company', 'fund', 'transaction')"),)


class Person(Base):
    __tablename__ = "people"
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)


class Company(Base):
    __tablename__ = "companies"
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)


class Fund(Base):
    __tablename__ = "funds"
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)


class TransactionOnCompany(Base):
    __tablename__ = "transactions_on_companies"
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.entity_id"), index=True)
    # Round, amounts, dates, participants and terms are assertions, never global columns.


class Source(Record, Base):
    __tablename__ = "sources"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    attribution: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="received")
    provider_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Assertion(Record, Base):
    __tablename__ = "assertions"
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    field: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    signal: Mapped[str] = mapped_column(String(20), default="reported")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    # Safe attribution is deliberately copied, not read from the raw source on export.
    attribution: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        CheckConstraint("signal IN ('confirmed', 'reported', 'hearsay')"),
        CheckConstraint("NOT (is_public AND is_internal)"),
    )


class EntityState(Base):
    __tablename__ = "entity_states"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="new")
    __table_args__ = (
        CheckConstraint("status IN ('new', 'reviewing', 'shared', 'on-hold', 'passed')"),
    )


class Watchlist(Record, Base):
    __tablename__ = "watchlists"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(20), default="selected")
    __table_args__ = (CheckConstraint("mode IN ('selected', 'all_knowledge')"),)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    watchlist_id: Mapped[str] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True
    )
    assertion_id: Mapped[str] = mapped_column(ForeignKey("assertions.id"), primary_key=True)


class Grant(Record, Base):
    __tablename__ = "grants"
    watchlist_id: Mapped[str] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"))
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND organisation_id IS NULL) OR (user_id IS NULL AND organisation_id IS NOT NULL)"
        ),
        UniqueConstraint("watchlist_id", "user_id"),
        UniqueConstraint("watchlist_id", "organisation_id"),
    )


class ChannelIdentity(Record, Base):
    __tablename__ = "channel_identities"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    channel: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(320))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("channel", "address"),)


class WebhookEvent(Record, Base):
    __tablename__ = "webhook_events"
    provider: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("provider", "external_id"),)


class Job(Record, Base):
    __tablename__ = "jobs"
    kind: Mapped[str] = mapped_column(String(40))
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_error: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (Index("ix_jobs_ready", "status", "available_at"),)


class Subscription(Record, Base):
    __tablename__ = "subscriptions"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="unconfigured")
    price_id: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    # Never include message bodies or assertion values in audit records.
