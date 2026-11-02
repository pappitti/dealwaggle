from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["company", "person", "fund", "transaction"]
Signal = Literal["confirmed", "reported", "hearsay"]
Visibility = Literal["team", "private"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Capture(Input):
    name: str = Field(min_length=1, max_length=200)
    kind: Kind = "company"
    entity_id: str | None = None
    company_id: str | None = None
    organisation_id: str
    visibility: Visibility = "team"
    field: str = Field(default="update", min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=10000)
    signal: Signal = "reported"
    attribution: str = Field(min_length=1, max_length=200)
    is_internal: bool = False
    source_id: str | None = None


class MessageIn(Input):
    body: str = Field(min_length=1, max_length=50000)
    organisation_id: str
    visibility: Visibility = "team"


class VisibilityIn(Input):
    visibility: Visibility
    organisation_id: str


class StateIn(Input):
    status: Literal["new", "reviewing", "shared", "on-hold", "passed"]


class WatchlistIn(Input):
    name: str = Field(min_length=1, max_length=120)
    mode: Literal["selected", "all_knowledge"] = "selected"


class ItemsIn(Input):
    assertion_ids: list[str] = Field(min_length=1, max_length=100)


class GrantIn(Input):
    user_id: str | None = None
    organisation_id: str | None = None

    @model_validator(mode="after")
    def exactly_one(self):
        if bool(self.user_id) == bool(self.organisation_id):
            raise ValueError("Choose exactly one person or organisation")
        return self


class DraftIn(ItemsIn):
    pass


class BillingIn(Input):
    organisation_id: str


class EnrichIn(Input):
    organisation_id: str
    linkedin_url: str = Field(max_length=500)
