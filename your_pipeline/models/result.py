from typing import Literal
from pydantic import BaseModel

class PriceResult(BaseModel):
    sku: str
    computed_price: float
    target_margin_used: float
    total_cost: float
    vendor_extra_cost_applied: float
    rule_source: Literal["brand", "vendor_category", "category", "vendor", "default"]
