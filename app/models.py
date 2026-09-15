from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StockStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    ERROR = "ERROR"


class Product(BaseModel):
    id: str
    name: str
    stock_quantity: int = Field(ge=0)


class ProductSearchResult(BaseModel):
    products: list[Product]


class ProductStockResult(BaseModel):
    found: bool
    product: Product | None = None


class TraceEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    request_id: str
    component: str
    event: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class CustomerRequest(BaseModel):
    message: str = Field(min_length=2, max_length=500)
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class CustomerResponse(BaseModel):
    request_id: str
    status: StockStatus
    customer_message: str
    product: Product | None = None
    trace: list[TraceEvent] = Field(default_factory=list)


class OutOfStockEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = "OUT_OF_STOCK"
    request_id: str
    product_id: str
    product_name: str
    stock_quantity: int = 0
    occurred_at: datetime = Field(default_factory=utc_now)


class TelegramResult(BaseModel):
    request_id: str
    success: bool
    dry_run: bool
    message_text: str
    trace: list[TraceEvent] = Field(default_factory=list)

