import os
from uuid import uuid4

import pytest
from dealwaggle.config import get_settings
from dealwaggle.db import get_session
from dealwaggle.main import create_app
from dealwaggle.seed import seed
from dealwaggle_db.models import Base, Membership, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("DEALWAGGLE_DEMO_MODE", "true")
    monkeypatch.setenv("DEALWAGGLE_ENVIRONMENT", "test")
    get_settings.cache_clear()
    postgres_url = os.environ.get("TEST_DATABASE_URL")
    schema = "test_" + uuid4().hex
    admin = None
    if postgres_url:
        admin = create_engine(postgres_url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        users = {user.auth_subject.split(":")[1]: user.id for user in session.scalars(select(User))}
        org = session.scalar(
            select(Membership.organisation_id).where(Membership.user_id == users["alice"])
        )

    def session_override():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client, engine, users, org
    engine.dispose()
    if admin:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
    get_settings.cache_clear()


def headers(persona):
    return {"x-demo-user": persona}


def capture(client, org, visibility="team", **kwargs):
    response = client.post(
        "/api/captures",
        json={
            "name": "Private prospect",
            "kind": "company",
            "value": "Confidential raise details",
            "attribution": "Named source",
            "organisation_id": org,
            "visibility": visibility,
            **kwargs,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
