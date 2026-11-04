from typing import Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .semantics import ENTITIES, FIELDS

Entity = Literal[tuple(ENTITIES)]
Canonical = Literal[tuple([*FIELDS, "ignore"])]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FieldProposal(Model):
    column_index: int = Field(ge=1)
    field: Canonical
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(max_length=500)
    alternatives: list[Canonical] = Field(default_factory=list, max_length=3)


class TableProposal(Model):
    table_id: str
    entity: Entity
    confidence: float = Field(ge=0, le=1)
    fields: list[FieldProposal]
    warnings: list[str]
    header_row: int | None = Field(default=None, ge=1)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class SemanticPlan(Model):
    tables: list[TableProposal]
    summary: str


class MappingInput(Model):
    entity: Entity
    fields: dict[str, Canonical]
    header_row: int = Field(ge=1)
    expected_revision: int = Field(ge=0)
    confirm: bool = True
    ignore: bool = False
    constants: dict[Literal["currency"], str] = Field(default_factory=dict)


class AnalyzeInput(Model):
    table_ids: list[str] = Field(default_factory=list, max_length=30)
    include_confirmed: bool = False


class RegionInput(Model):
    sheet: str
    ref: str
    header_row: int = Field(ge=1)


class ReviewInput(Model):
    decision: Literal["approve", "reject"]


class AgentInput(Model):
    message: str = Field(min_length=1, max_length=2000)
    mode: Literal["meta", "guided"] = "meta"
    task: Literal["custom", "daily_review", "sales_review", "stock_review", "supplier_review", "replenishment"] = "custom"
    request_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    durable: bool = False
    expected_fingerprint: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')


class EmptyArgs(Model):
    pass


class InventoryArgs(Model):
    product_ids: list[str] = Field(default_factory=list, max_length=1)


class SalesArgs(Model):
    product_id: str | None = Field(default=None, min_length=1, max_length=180)
    date_from: date | None = None
    date_to: date | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("The start date must precede or equal the end date.")
        return self


class SalesFilter(Model):
    field: Literal["product_id", "date_from", "date_to", "currency"]
    value: str = Field(min_length=1, max_length=180)


class SalesSelection(Model):
    filters: list[SalesFilter] = Field(default_factory=list, max_length=4)

    def scope(self):
        fields = {f.field: f.value for f in self.filters}
        if len(fields) != len(self.filters):
            raise ValueError("Each sales filter may appear once.")
        return SalesArgs.model_validate_strings(fields)


class DraftArgs(Model):
    product_ids: list[str] = Field(max_length=100)


class ComparisonFilter(Model):
    field: Literal["product_id", "currency"]
    value: str = Field(min_length=1, max_length=180)


class ComparisonArgs(Model):
    window_days: int = Field(default=7, ge=1, le=90)
    filters: list[ComparisonFilter] = Field(default_factory=list, max_length=2)

    def scope(self):
        fields = {f.field: f.value for f in self.filters}
        if len(fields) != len(self.filters):
            raise ValueError("Each comparison filter may appear once.")
        return SalesArgs.model_validate_strings(fields)


class Ping(Model):
    ok: bool


class DemandParameters(Model):
    window_days: int = Field(default=30, ge=7, le=365)
    lead_time_days: int = Field(default=7, ge=1, le=365)
    safety_days: int = Field(default=3, ge=0, le=365)
    review_period_days: int = Field(default=14, ge=1, le=365)
    as_of: str | None = None


class DemandPolicyInput(DemandParameters):
    expected_revision: int = Field(ge=0)
    enabled: bool = True
    stock_snapshot_confirmed: bool = False
