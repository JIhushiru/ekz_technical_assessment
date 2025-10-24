from typing import Optional
from pydantic import BaseModel, Field


class Product(BaseModel):
    """Represents a product offered by a vendor.

    Each product has a name, SKU, cost, and is linked to a category, brand, and optionally a shipping tier.
    The product is associated with a specific vendor via `vendor_id`.
    """

    name: str = Field(..., description="The name of the product")
    sku: str = Field(..., description="Unique identifier for the product")
    cost: float = Field(..., description="The cost price of the product")
    shipping_tier_id: Optional[int] = Field(
        None, description="Optional ID representing the shipping tier for the product"
    )
    category_id: int = Field(
        ..., description="The ID of the category this product belongs to"
    )
    vendor_id: int = Field(
        ..., description="The ID of the vendor offering this product"
    )
    brand_id: int = Field(
        ..., description="The ID of the brand associated with this product"
    )
