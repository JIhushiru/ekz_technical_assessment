from pydantic import BaseModel, Field


class ShippingTier(BaseModel):
    """Represents a shipping tier associated with a vendor.

    Defines different shipping levels with their corresponding costs,
    linked to a vendor via `vendor_id`.
    """

    shipping_tier: str = Field(..., description="The level of the shipping tier")
    shipping_tier_id: int = Field(
        ..., description="A unique identifier for the shipping tier"
    )
    vendor_id: int = Field(
        ..., description="The ID of the vendor associated with this shipping tier"
    )
    shipping_cost: int = Field(
        ..., description="The cost associated with this shipping tier"
    )
