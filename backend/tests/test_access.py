from conftest import capture, headers
from dealwaggle_db.models import Assertion, Membership, Source
from sqlalchemy.orm import Session


def test_team_default_and_private_exception(context):
    client, _, _, org = context
    shared = capture(client, org)
    private = capture(client, org, "private")
    assert (
        client.get(f"/api/entities/{shared['entity_id']}", headers=headers("ben")).status_code
        == 200
    )
    assert (
        client.get(f"/api/entities/{private['entity_id']}", headers=headers("ben")).status_code
        == 404
    )
    assert (
        client.get(f"/api/entities/{shared['entity_id']}", headers=headers("outsider")).status_code
        == 404
    )
    outsider_rows = client.get("/api/entities?q=Private", headers=headers("outsider")).json()
    assert outsider_rows == []


def test_selected_sharing_does_not_expose_other_facts_or_raw_source(context):
    client, engine, users, org = context
    first = capture(client, org, "private", value="Safe to share")
    hidden = capture(client, org, "private", entity_id=first["entity_id"], value="Hidden valuation")
    with Session(engine) as session:
        fact = session.get(Assertion, first["assertion_id"])
        session.get(Source, fact.source_id).body = "Do not expose this original message"
        session.commit()
    watchlist = client.post("/api/watchlists", json={"name": "Selected"}).json()["id"]
    assert (
        client.post(
            f"/api/watchlists/{watchlist}/items", json={"assertion_ids": [first["assertion_id"]]}
        ).status_code
        == 204
    )
    grant = client.post(
        f"/api/watchlists/{watchlist}/grants", json={"user_id": users["outsider"]}
    ).json()["id"]
    response = client.get(f"/api/entities/{first['entity_id']}", headers=headers("outsider"))
    assert len(response.json()["assertions"]) == 1
    assert hidden["assertion_id"] not in response.text
    assert "original message" not in response.text and "source_id" not in response.text
    assert client.get("/api/inbox", headers=headers("outsider")).json() == []
    assert (
        client.post(
            "/api/drafts",
            json={"assertion_ids": [first["assertion_id"]]},
            headers=headers("outsider"),
        ).status_code
        == 403
    )
    client.delete(f"/api/watchlists/{watchlist}/grants/{grant}")
    assert (
        client.get(f"/api/entities/{first['entity_id']}", headers=headers("outsider")).status_code
        == 404
    )


def test_organisation_grant_and_membership_revocation(context):
    client, engine, users, org = context
    private = capture(client, org, "private")
    watchlist = client.post("/api/watchlists", json={"name": "Team shortlist"}).json()["id"]
    client.post(
        f"/api/watchlists/{watchlist}/items", json={"assertion_ids": [private["assertion_id"]]}
    )
    client.post(f"/api/watchlists/{watchlist}/grants", json={"organisation_id": org})
    assert (
        client.get(f"/api/entities/{private['entity_id']}", headers=headers("ben")).status_code
        == 200
    )
    with Session(engine) as session:
        session.delete(session.get(Membership, (users["ben"], org)))
        session.commit()
    assert client.get("/api/entities", headers=headers("ben")).json() == []


def test_cannot_publish_or_impersonate(context):
    client, _, users, org = context
    base = {"name": "Injected", "value": "No", "attribution": "me", "organisation_id": org}
    assert client.post("/api/captures", json={**base, "is_public": True}).status_code == 422
    assert client.post("/api/captures", json={**base, "owner_id": users["ben"]}).status_code == 422
    assert client.post("/api/captures", json=base, headers=headers("outsider")).status_code == 403


def test_internal_and_received_facts_cannot_be_reshared(context):
    client, _, _, org = context
    internal = capture(client, org, is_internal=True)
    watchlist = client.post("/api/watchlists", json={"name": "Test"}).json()["id"]
    assert (
        client.post(
            f"/api/watchlists/{watchlist}/items", json={"assertion_ids": [internal["assertion_id"]]}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/drafts", json={"assertion_ids": [internal["assertion_id"]]}).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/watchlists/{watchlist}/grants",
            json={"organisation_id": org},
            headers=headers("ben"),
        ).status_code
        == 404
    )


def test_dynamic_all_knowledge_includes_future_facts_excludes_internal(context):
    client, _, users, org = context
    watchlist = client.post(
        "/api/watchlists", json={"name": "All", "mode": "all_knowledge"}
    ).json()["id"]
    client.post(f"/api/watchlists/{watchlist}/grants", json={"user_id": users["outsider"]})
    future = capture(client, org, "private")
    secret_note = capture(client, org, "private", is_internal=True)
    assert (
        client.get(f"/api/entities/{future['entity_id']}", headers=headers("outsider")).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/entities/{secret_note['entity_id']}", headers=headers("outsider")
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/assertions/{future['assertion_id']}/visibility",
            json={"visibility": "private", "organisation_id": org},
        ).status_code
        == 409
    )


def test_make_private_removes_team_and_selected_grants(context):
    client, _, users, org = context
    shared = capture(client, org)
    watchlist = client.post("/api/watchlists", json={"name": "Test"}).json()["id"]
    client.post(
        f"/api/watchlists/{watchlist}/items", json={"assertion_ids": [shared["assertion_id"]]}
    )
    client.post(f"/api/watchlists/{watchlist}/grants", json={"user_id": users["outsider"]})
    assert (
        client.patch(
            f"/api/assertions/{shared['assertion_id']}/visibility",
            json={"visibility": "private", "organisation_id": org},
        ).status_code
        == 200
    )
    for persona in ("ben", "outsider"):
        assert (
            client.get(f"/api/entities/{shared['entity_id']}", headers=headers(persona)).status_code
            == 404
        )


def test_drafts_preserve_evidence_and_link_not_raw_message(context):
    client, engine, _, org = context
    fact = capture(client, org, signal="hearsay", value="May raise next year")
    with Session(engine) as session:
        source = session.get(Source, session.get(Assertion, fact["assertion_id"]).source_id)
        source.body = "private raw forward"
        session.commit()
    result = client.post("/api/drafts", json={"assertion_ids": [fact["assertion_id"]]}).json()
    assert "(hearsay)" in result["text"] and "Named source" in result["text"]
    assert f"?entity={fact['entity_id']}" in result["text"]
    assert "private raw forward" not in result["text"]


def test_private_source_and_transaction_constraints(context):
    client, _, _, org = context
    company = capture(client, org, "private")
    transaction = capture(
        client, org, "private", kind="transaction", company_id=company["entity_id"]
    )
    assert (
        client.get(f"/api/entities/{transaction['entity_id']}", headers=headers("ben")).status_code
        == 404
    )
    bad = client.post(
        "/api/captures",
        json={
            "name": "Bad",
            "kind": "transaction",
            "value": "No company",
            "attribution": "Me",
            "organisation_id": org,
        },
    )
    assert bad.status_code == 422
    assert client.get("/api/entities?q=Bad").json() == []


def test_search_does_not_leak_private_fact_count(context):
    client, _, _, org = context
    public = capture(client, org)
    capture(client, org, "private", entity_id=public["entity_id"], value="Hidden second fact")
    row = next(
        item
        for item in client.get("/api/entities", headers=headers("ben")).json()
        if item["id"] == public["entity_id"]
    )
    assert row["fact_count"] == 1
    assert "Hidden second fact" not in str(row)
