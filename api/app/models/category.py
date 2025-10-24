from pydantic import BaseModel, Field


class Category(BaseModel):
    """Represents a product category associated with a vendor.

    Includes the category's name, its unique ID, and the ID of the vendor it belongs to.
    """

    name: str = Field(..., description="The name of the category")
    category_id: int = Field(..., description="A unique identifier for the category")
    vendor_id: int = Field(
        ..., description="The ID of the vendor associated with the category"
    )
