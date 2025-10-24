from pydantic import BaseModel, Field


class Brand(BaseModel):
    """Represents a brand associated with a vendor.

    Includes the brand's name, its unique ID, and the ID of the vendor it belongs to.
    """

    name: str = Field(..., description="The name of the brand")
    brand_id: int = Field(..., description="A unique identifier for the brand")
    vendor_id: int = Field(
        ..., description="The ID of the vendor associated with the brand"
    )
