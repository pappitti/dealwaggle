from urllib.parse import urlparse

from dealwaggle_db.models import (
    Assertion,
    AuditEvent,
    Company,
    Entity,
    EntityState,
    Fund,
    Grant,
    Job,
    Membership,
    Organisation,
    Person,
    Source,
    Subscription,
    TransactionOnCompany,
    User,
    Watchlist,
    WatchlistItem,
    uid,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from dealwaggle.access import facts_for, organisation_ids, visible_assertion
from dealwaggle.auth import current_user, require_member
from dealwaggle.config import get_settings
from dealwaggle.db import get_session
from dealwaggle.schemas import (
    BillingIn,
    Capture,
    DraftIn,
    EnrichIn,
    GrantIn,
    ItemsIn,
    MessageIn,
    StateIn,
    VisibilityIn,
    WatchlistIn,
)

router = APIRouter(prefix="/api")


def audit(session, user, action, target):
    session.add(AuditEvent(actor_id=user.id, action=action, target_id=target))


def assertion_json(fact: Assertion, user: User):
    return {
        "id": fact.id,
        "entity_id": fact.entity_id,
        "field": fact.field,
        "value": fact.value,
        "signal": fact.signal,
        "is_internal": fact.is_internal,
        "visibility": "public" if fact.is_public else "team" if fact.organisation_id else "private",
        "attribution": fact.attribution,
        "channel": fact.channel,
        "observed_at": fact.observed_at,
        "owned": fact.owner_id == user.id,
        "can_forward": not fact.is_internal and (fact.owner_id == user.id or fact.is_public),
    }


def owned_watchlist(session, user, watchlist_id):
    watchlist = session.get(Watchlist, watchlist_id)
    if not watchlist or watchlist.owner_id != user.id:
        raise HTTPException(404, "Watchlist not found")
    return watchlist


@router.get("/me")
def me(user: User = Depends(current_user), session: Session = Depends(get_session)):
    memberships = session.execute(
        select(Organisation, Membership.role).join(Membership).where(Membership.user_id == user.id)
    ).all()
    return {
        "id": user.id,
        "name": user.name,
        "demo": get_settings().demo_mode,
        "organisations": [
            {"id": org.id, "name": org.name, "role": role} for org, role in memberships
        ],
    }


@router.get("/team")
def team(user: User = Depends(current_user), session: Session = Depends(get_session)):
    users = session.scalars(
        select(User)
        .join(Membership)
        .where(Membership.organisation_id.in_(organisation_ids(user.id)))
        .distinct()
    ).all()
    return [{"id": member.id, "name": member.name} for member in users]


@router.get("/entities")
def entities(
    q: str = Query("", max_length=200),
    kind: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    query = select(Entity).where(
        exists(
            select(Assertion.id).where(Assertion.entity_id == Entity.id, visible_assertion(user.id))
        )
    )
    if q:
        query = query.where(Entity.name.icontains(q, autoescape=True))
    if kind:
        query = query.where(Entity.kind == kind)
    result = []
    for entity in session.scalars(
        query.order_by(Entity.created_at.desc()).limit(limit).offset(offset)
    ):
        facts = facts_for(session, user.id, entity.id)
        state = session.get(EntityState, (user.id, entity.id))
        summary = next((fact for fact in facts if not fact.is_internal), facts[0])
        result.append(
            {
                "id": entity.id,
                "name": entity.name,
                "kind": entity.kind,
                "status": state.status if state else "new",
                "fact_count": len(facts),
                "summary": assertion_json(summary, user),
            }
        )
    return result


@router.get("/entities/{entity_id}")
def entity_detail(
    entity_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    facts = facts_for(session, user.id, entity_id)
    if not facts:
        raise HTTPException(404, "Record not found")
    entity = session.get(Entity, entity_id)
    return {
        "id": entity.id,
        "name": entity.name,
        "kind": entity.kind,
        "assertions": [assertion_json(fact, user) for fact in facts],
    }


@router.post("/captures", status_code=201)
def capture(
    data: Capture, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    require_member(session, user.id, data.organisation_id)
    entity = None
    if data.entity_id:
        if not facts_for(session, user.id, data.entity_id):
            raise HTTPException(404, "Record not found")
        entity = session.get(Entity, data.entity_id)
    if not entity:
        if data.kind == "transaction":
            company = session.get(Company, data.company_id) if data.company_id else None
            if not company or not facts_for(session, user.id, data.company_id):
                raise HTTPException(422, "A transaction needs a company you can access")
        entity = Entity(kind=data.kind, name=data.name)
        session.add(entity)
        session.flush()
        detail = {
            "person": Person,
            "company": Company,
            "fund": Fund,
            "transaction": TransactionOnCompany,
        }[data.kind]
        session.add(
            detail(
                entity_id=entity.id,
                **({"company_id": data.company_id} if data.kind == "transaction" else {}),
            )
        )
    org_id = data.organisation_id if data.visibility == "team" else None
    if data.source_id:
        source = session.get(Source, data.source_id)
        if not source or source.owner_id != user.id:
            raise HTTPException(404, "Source not found")
        source.status = "reviewed"
    else:
        source = Source(
            owner_id=user.id,
            organisation_id=org_id,
            channel="manual",
            attribution=data.attribution,
            body=data.value,
            status="reviewed",
        )
        session.add(source)
        session.flush()
    fact = Assertion(
        entity_id=entity.id,
        owner_id=user.id,
        organisation_id=org_id,
        source_id=source.id,
        field=data.field,
        value=data.value,
        signal=data.signal,
        attribution=data.attribution,
        channel=source.channel,
        observed_at=source.observed_at,
        is_internal=data.is_internal,
    )
    session.add(fact)
    session.flush()
    audit(session, user, "assertion.created", fact.id)
    session.commit()
    return {"entity_id": entity.id, "assertion_id": fact.id}


@router.patch("/assertions/{assertion_id}/visibility")
def change_visibility(
    assertion_id: str,
    data: VisibilityIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    require_member(session, user.id, data.organisation_id)
    fact = session.get(Assertion, assertion_id)
    if not fact or fact.owner_id != user.id or fact.is_public:
        raise HTTPException(404, "Editable fact not found")
    fact.organisation_id = data.organisation_id if data.visibility == "team" else None
    # Making a fact private also removes explicit selected sharing. Dynamic
    # all-knowledge grants still apply, so require their removal first.
    if data.visibility == "private":
        shared_all = session.scalar(
            select(Grant.id)
            .join(Watchlist)
            .where(Watchlist.owner_id == user.id, Watchlist.mode == "all_knowledge")
            .limit(1)
        )
        if shared_all and not fact.is_internal:
            raise HTTPException(
                409, "Revoke your all-knowledge watchlist grants before making this fact private"
            )
        for item in session.scalars(
            select(WatchlistItem).where(WatchlistItem.assertion_id == fact.id)
        ):
            session.delete(item)
    audit(session, user, "assertion.visibility_changed", fact.id)
    session.commit()
    return assertion_json(fact, user)


@router.put("/entities/{entity_id}/status")
def set_status(
    entity_id: str,
    data: StateIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    if not facts_for(session, user.id, entity_id):
        raise HTTPException(404, "Record not found")
    state = session.get(EntityState, (user.id, entity_id))
    if not state:
        state = EntityState(user_id=user.id, entity_id=entity_id)
        session.add(state)
    state.status = data.status
    session.commit()
    return {"status": state.status}


@router.post("/messages", status_code=202)
def message(
    data: MessageIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    require_member(session, user.id, data.organisation_id)
    source = Source(
        owner_id=user.id,
        organisation_id=data.organisation_id if data.visibility == "team" else None,
        channel="manual",
        attribution=user.name,
        body=data.body,
    )
    session.add(source)
    session.flush()
    session.add(
        Job(kind="extract", dedupe_key=f"extract:{source.id}", payload={"source_id": source.id})
    )
    session.commit()
    return {"id": source.id, "status": source.status}


@router.get("/inbox")
def inbox(user: User = Depends(current_user), session: Session = Depends(get_session)):
    # Raw messages remain with their forwarding user; reviewed facts use team defaults.
    sources = session.scalars(
        select(Source)
        .where(Source.owner_id == user.id, Source.status != "reviewed")
        .order_by(Source.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": source.id,
            "body": source.body,
            "channel": source.channel,
            "attribution": source.attribution,
            "status": source.status,
            "observed_at": source.observed_at,
            "organisation_id": source.organisation_id,
        }
        for source in sources
    ]


@router.get("/watchlists")
def watchlists(user: User = Depends(current_user), session: Session = Depends(get_session)):
    received = select(Grant.watchlist_id).where(
        or_(Grant.user_id == user.id, Grant.organisation_id.in_(organisation_ids(user.id)))
    )
    lists = session.scalars(
        select(Watchlist)
        .where(or_(Watchlist.owner_id == user.id, Watchlist.id.in_(received)))
        .order_by(Watchlist.created_at)
    ).all()
    result = []
    for item in lists:
        query = select(Assertion).where(
            Assertion.owner_id == item.owner_id, ~Assertion.is_internal, visible_assertion(user.id)
        )
        if item.mode == "selected":
            query = query.where(
                Assertion.id.in_(
                    select(WatchlistItem.assertion_id).where(WatchlistItem.watchlist_id == item.id)
                )
            )
        facts = session.scalars(query).all()
        grants = (
            session.scalars(select(Grant).where(Grant.watchlist_id == item.id)).all()
            if item.owner_id == user.id
            else []
        )
        result.append(
            {
                "id": item.id,
                "name": item.name,
                "mode": item.mode,
                "owned": item.owner_id == user.id,
                "assertions": [assertion_json(fact, user) for fact in facts],
                "grants": [
                    {
                        "id": grant.id,
                        "user_id": grant.user_id,
                        "organisation_id": grant.organisation_id,
                    }
                    for grant in grants
                ],
            }
        )
    return result


@router.post("/watchlists", status_code=201)
def create_watchlist(
    data: WatchlistIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    item = Watchlist(owner_id=user.id, name=data.name, mode=data.mode)
    session.add(item)
    session.flush()
    audit(session, user, "watchlist.created", item.id)
    session.commit()
    return {"id": item.id}


@router.post("/watchlists/{watchlist_id}/items", status_code=204)
def add_items(
    watchlist_id: str,
    data: ItemsIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    watchlist = owned_watchlist(session, user, watchlist_id)
    if watchlist.mode != "selected":
        raise HTTPException(
            409, "All-knowledge lists include all your non-internal facts automatically"
        )
    for fact_id in set(data.assertion_ids):
        fact = session.get(Assertion, fact_id)
        if not fact or fact.owner_id != user.id or fact.is_internal:
            raise HTTPException(403, "Only your own non-internal facts can be shared")
        if not session.get(WatchlistItem, (watchlist.id, fact_id)):
            session.add(WatchlistItem(watchlist_id=watchlist.id, assertion_id=fact_id))
    audit(session, user, "watchlist.items_added", watchlist.id)
    session.commit()
    return Response(status_code=204)


@router.delete("/watchlists/{watchlist_id}/items/{assertion_id}", status_code=204)
def remove_item(
    watchlist_id: str,
    assertion_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    owned_watchlist(session, user, watchlist_id)
    item = session.get(WatchlistItem, (watchlist_id, assertion_id))
    if item:
        session.delete(item)
        audit(session, user, "watchlist.item_removed", watchlist_id)
        session.commit()
    return Response(status_code=204)


@router.post("/watchlists/{watchlist_id}/grants", status_code=201)
def grant_access(
    watchlist_id: str,
    data: GrantIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    owned_watchlist(session, user, watchlist_id)
    target = (
        session.get(User, data.user_id)
        if data.user_id
        else session.get(Organisation, data.organisation_id)
    )
    if not target:
        raise HTTPException(404, "Recipient not found")
    existing = session.scalar(
        select(Grant).where(
            Grant.watchlist_id == watchlist_id,
            Grant.user_id == data.user_id,
            Grant.organisation_id == data.organisation_id,
        )
    )
    if existing:
        return {"id": existing.id}
    grant = Grant(
        watchlist_id=watchlist_id, user_id=data.user_id, organisation_id=data.organisation_id
    )
    session.add(grant)
    session.flush()
    audit(session, user, "grant.created", grant.id)
    session.commit()
    return {"id": grant.id}


@router.delete("/watchlists/{watchlist_id}/grants/{grant_id}", status_code=204)
def revoke_access(
    watchlist_id: str,
    grant_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    owned_watchlist(session, user, watchlist_id)
    grant = session.get(Grant, grant_id)
    if grant and grant.watchlist_id == watchlist_id:
        session.delete(grant)
        audit(session, user, "grant.revoked", grant.id)
        session.commit()
    return Response(status_code=204)


@router.post("/drafts")
def draft(
    data: DraftIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    facts = []
    for fact_id in dict.fromkeys(data.assertion_ids):
        fact = session.scalar(
            select(Assertion).where(Assertion.id == fact_id, visible_assertion(user.id))
        )
        if not fact or fact.is_internal or (fact.owner_id != user.id and not fact.is_public):
            raise HTTPException(
                403,
                "You can forward only your own facts or public facts; internal notes stay internal",
            )
        facts.append(fact)
    lines = []
    for fact in facts:
        entity = session.get(Entity, fact.entity_id)
        lines.extend(
            [
                f"*{entity.name}*: {fact.value} ({fact.signal})",
                f"Source: {fact.attribution} · {fact.channel} · {fact.observed_at:%d %b %Y}",
            ]
        )
    lines.extend(
        [
            "",
            "Interested? I can make the introduction.",
            f"View in DealWaggle: {get_settings().app_url.rstrip('/')}/?entity={facts[0].entity_id}",
        ]
    )
    audit(session, user, "draft.prepared", facts[0].id)
    session.commit()
    return {"text": "\n".join(lines), "requires_access": True}


@router.get("/billing/{organisation_id}")
def billing_status(
    organisation_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    require_member(session, user.id, organisation_id)
    subscription = session.scalar(
        select(Subscription).where(Subscription.organisation_id == organisation_id)
    )
    settings = get_settings()
    return {
        "status": subscription.status if subscription else "unconfigured",
        "configured": bool(
            settings.stripe_secret_key
            and settings.stripe_price_id
            and settings.stripe_webhook_secret
        ),
        "premium": bool(
            subscription
            and subscription.status in ("active", "trialing")
            and subscription.price_id == settings.stripe_price_id
            and settings.stripe_price_id
        ),
    }


@router.post("/billing/checkout")
def checkout(
    data: BillingIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    from dealwaggle.billing import checkout_url

    require_member(session, user.id, data.organisation_id, owner=True)
    return {"url": checkout_url(session, data.organisation_id)}


@router.post("/billing/portal")
def portal(
    data: BillingIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    from dealwaggle.billing import portal_url

    require_member(session, user.id, data.organisation_id, owner=True)
    return {"url": portal_url(session, data.organisation_id)}


@router.post("/entities/{entity_id}/enrich", status_code=202)
def enrich(
    entity_id: str,
    data: EnrichIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    require_member(session, user.id, data.organisation_id)
    facts = facts_for(session, user.id, entity_id)
    if not facts:
        raise HTTPException(404, "Record not found")
    if session.get(Entity, entity_id).kind != "person":
        raise HTTPException(422, "LinkedIn enrichment is for people")
    parsed = urlparse(data.linkedin_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in ("linkedin.com", "www.linkedin.com")
        or not parsed.path.startswith("/in/")
    ):
        raise HTTPException(422, "Use an HTTPS LinkedIn profile URL")
    if not billing_status(data.organisation_id, user, session)["premium"]:
        raise HTTPException(402, "Enrichment requires an active subscription")
    job = Job(
        kind="enrich_person",
        dedupe_key=f"enrich:{uid()}",
        payload={
            "entity_id": entity_id,
            "owner_id": user.id,
            "organisation_id": data.organisation_id,
            "url": data.linkedin_url,
        },
    )
    session.add(job)
    session.commit()
    return {"id": job.id, "status": job.status}
