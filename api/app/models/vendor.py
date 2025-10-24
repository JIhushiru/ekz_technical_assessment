from pydantic import BaseModel, Field


class Vendor(BaseModel):
    """Contains the unique vendor ID and the vendor's name."""

    vendor_id: int = Field(..., description="A unique identifier for the vendor")
    name: str = Field(..., description="The name of the vendor")
