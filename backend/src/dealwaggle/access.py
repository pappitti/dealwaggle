"""One query predicate for every fact read, including search and entity discovery."""

from dealwaggle_db.models import Assertion, Grant, Membership, Watchlist, WatchlistItem
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session


def organisation_ids(user_id: str):
    return select(Membership.organisation_id).where(Membership.user_id == user_id)


def visible_assertion(user_id: str):
    recipient = or_(Grant.user_id == user_id, Grant.organisation_id.in_(organisation_ids(user_id)))
    selected = exists(
        select(WatchlistItem.assertion_id)
        .where(
            WatchlistItem.watchlist_id == Watchlist.id,
            WatchlistItem.assertion_id == Assertion.id,
        )
        .correlate(Watchlist, Assertion)
    )
    shared = exists(
        select(Grant.id)
        .join(Watchlist, Grant.watchlist_id == Watchlist.id)
        .where(
            recipient,
            Watchlist.owner_id == Assertion.owner_id,
            ~Assertion.is_internal,
            or_(Watchlist.mode == "all_knowledge", selected),
        )
        .correlate(Assertion)
    )
    return or_(
        Assertion.is_public,
        Assertion.owner_id == user_id,
        Assertion.organisation_id.in_(organisation_ids(user_id)),
        shared,
    )


def facts_for(session: Session, user_id: str, entity_id: str):
    return session.scalars(
        select(Assertion)
        .where(
            Assertion.entity_id == entity_id,
            visible_assertion(user_id),
        )
        .order_by(Assertion.created_at.desc())
    ).all()
