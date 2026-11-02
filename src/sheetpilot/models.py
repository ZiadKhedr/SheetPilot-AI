from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Entity = Literal["sales", "inventory", "suppliers", "unknown"]
Canonical = Literal["product_id", "product_name", "order_id", "quantity", "unit_price", "revenue",
                    "sale_date", "stock_quantity", "reorder_point", "target_stock",
                    "supplier_id", "supplier_name", "unit_cost", "currency", "supplier_email", "ignore"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldProposal(Model):
    column_index: int = Field(ge=1)
    field: Canonical
    confidence: float = Field(ge=0, le=1)
    evidence: str


class TableProposal(Model):
    table_id: str
    entity: Entity
    confidence: float = Field(ge=0, le=1)
    fields: list[FieldProposal]
    warnings: list[str]


class SemanticPlan(Model):
    tables: list[TableProposal]
    summary: str


class MappingInput(Model):
    entity: Entity
    fields: dict[str, Canonical]
    header_row: int = Field(ge=1)
    expected_revision: int = Field(ge=0)
    confirm: bool = True


class RegionInput(Model):
    sheet: str
    ref: str
    header_row: int = Field(ge=1)


class ReviewInput(Model):
    decision: Literal["approve", "reject"]


class AgentInput(Model):
    message: str = Field(min_length=1, max_length=2000)
    mode: Literal["meta", "guided"] = "meta"


class EmptyArgs(Model):
    pass


class DraftArgs(Model):
    product_ids: list[str] = Field(max_length=100)


class Ping(Model):
    ok: bool
