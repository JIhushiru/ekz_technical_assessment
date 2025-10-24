from typing import Optional
from pydantic import BaseModel, Field, field_validator

class ProductIn(BaseModel):
    sku: str
    vendor_name: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    cost: float = Field(ge=0)
    # None => shipping tier is null (brand rule may apply; shipping cost treated as 0)
    shipping_cost: Optional[float] = Field(default=None, ge=0)

    @field_validator("sku", "vendor_name")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("must not be blank")
        return v
