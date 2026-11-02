"""Idempotent, explicitly opt-in fictional demo data. Never run in production."""

from dealwaggle_db.models import (
    Assertion,
    Company,
    Entity,
    EntityState,
    Fund,
    Membership,
    Organisation,
    Person,
    Source,
    TransactionOnCompany,
    User,
    Watchlist,
    WatchlistItem,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from dealwaggle.config import get_settings
from dealwaggle.db import get_engine


def seed(session):
    existing = session.scalar(select(User).where(User.auth_subject == "demo:alice"))
    if existing:
        return
    alice = User(auth_subject="demo:alice", name="Claire Martin", email="claire@example.test")
    ben = User(auth_subject="demo:ben", name="Marc Dubois", email="marc@example.test")
    outsider = User(auth_subject="demo:outsider", name="Sofia Rossi", email="sofia@example.test")
    team = Organisation(name="Fieldwork Ventures")
    other = Organisation(name="Rossi Capital")
    session.add_all([alice, ben, outsider, team, other])
    session.flush()
    session.add_all(
        [
            Membership(user_id=alice.id, organisation_id=team.id, role="owner"),
            Membership(user_id=ben.id, organisation_id=team.id),
            Membership(user_id=outsider.id, organisation_id=other.id, role="owner"),
        ]
    )
    session.flush()
    records = [
        (
            "Orbital Robotics",
            "company",
            "Raising €4m seed for warehouse picking robots. Looking for a lead investor.",
            "reported",
            "WhatsApp from a founder contact",
            "whatsapp",
            "new",
        ),
        (
            "Noma Health",
            "company",
            "Piloting care coordination software with three clinics in France.",
            "confirmed",
            "Founder presentation",
            "email",
            "reviewing",
        ),
        (
            "Terrawatt",
            "company",
            "May open a €6m round next spring for industrial energy storage.",
            "hearsay",
            "Conversation with an investor",
            "manual",
            "new",
        ),
        (
            "Léa Moreau",
            "person",
            "Co-founder of Orbital Robotics. Previously led a warehouse automation team.",
            "reported",
            "Introduction from Marc",
            "email",
            "new",
        ),
        (
            "Northstar Fund II",
            "fund",
            "A new early-stage fund focused on European industrial technology.",
            "reported",
            "Fund manager introduction",
            "email",
            "on-hold",
        ),
        (
            "Orbital seed round",
            "transaction",
            "€4m target; lead and final terms are still to be confirmed.",
            "reported",
            "Founder update",
            "whatsapp",
            "reviewing",
        ),
    ]
    facts = []
    company_id = None
    for name, kind, value, signal, attribution, channel, status in records:
        entity = Entity(name=name, kind=kind)
        source = Source(
            owner_id=alice.id,
            organisation_id=team.id,
            channel=channel,
            attribution=attribution + " (fictional demo)",
            body=value,
            status="reviewed",
        )
        session.add_all([entity, source])
        session.flush()
        if kind == "company":
            session.add(Company(entity_id=entity.id))
            company_id = company_id or entity.id
        elif kind == "person":
            session.add(Person(entity_id=entity.id))
        elif kind == "fund":
            session.add(Fund(entity_id=entity.id))
        else:
            session.add(TransactionOnCompany(entity_id=entity.id, company_id=company_id))
        fact = Assertion(
            entity_id=entity.id,
            source_id=source.id,
            owner_id=alice.id,
            organisation_id=team.id,
            field="update",
            value=value,
            signal=signal,
            attribution=source.attribution,
            channel=channel,
        )
        session.add(fact)
        session.add(EntityState(user_id=alice.id, entity_id=entity.id, status=status))
        session.flush()
        facts.append(fact)
    session.add(
        Assertion(
            entity_id=company_id,
            source_id=facts[0].source_id,
            owner_id=alice.id,
            organisation_id=team.id,
            field="note",
            value="Ask for customer references before scheduling partner review.",
            signal="hearsay",
            is_internal=True,
            attribution="Claire Martin (fictional demo)",
            channel="manual",
        )
    )
    watchlist = Watchlist(owner_id=alice.id, name="Industrial technology", mode="selected")
    session.add(watchlist)
    session.flush()
    session.add(WatchlistItem(watchlist_id=watchlist.id, assertion_id=facts[0].id))
    session.commit()


def main():
    settings = get_settings()
    if not settings.demo_mode or settings.environment == "production":
        raise SystemExit(
            "Enable DEALWAGGLE_DEMO_MODE only in a local development environment to seed data"
        )
    with Session(get_engine()) as session:
        seed(session)
    print("Fictional demo ready: Claire (alice), Marc (ben), Sofia (outsider).")


if __name__ == "__main__":
    main()
