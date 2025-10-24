from typing import Optional
from pydantic import BaseModel

class RepricedOut(BaseModel):
    sku: str
    computed_price: float
    rule_source: str
    target_margin_used: float
    total_cost: float
    vendor_extra_cost_applied: float
    vendor_id: Optional[int] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    name: Optional[str] = None