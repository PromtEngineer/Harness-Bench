"""Order data model."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LineItem:
    sku: str
    qty: int
    price_cents: int


@dataclass
class Order:
    order_id: str
    region: str
    coupon: Optional[str]
    items: List[LineItem]
