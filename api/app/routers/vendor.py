from typing import List
import logging

from fastapi import APIRouter, Depends, status, Request, Path, HTTPException
from pydantic import TypeAdapter

from api.app.auth.dependencies import verify_api_key
from api.app.models.vendor import Vendor
from api.app.models.shipping_tiers import ShippingTier
from api.app.models.response import StandardResponse

router = APIRouter(
    prefix="/api/v1/vendors",
    tags=["vendors"],
    responses={404: {"description": "Not Found"}},
)


@router.get(
    "/",
    response_model=StandardResponse[Vendor],
    summary="Get all vendors",
    description="Returns a list of vendors.",
)
def get_vendors(
    request: Request, _api_key: str = Depends(verify_api_key)
) -> StandardResponse[Vendor]:
    """Queries all the vendors.

    Args:
        request (Request): The request instance.
        _api_key (str): API key for authorization.

    Returns:
        StandardResponse[Vendor]: Standard response containing a list of vendors.
    """
    raw_data = request.app.state.vendors
    vendors = TypeAdapter(List[Vendor])
    data = vendors.validate_python(raw_data)
    return StandardResponse(
        status="success",
        code=status.HTTP_200_OK,
        message=f"Queried {len(data)} vendors.",
        data=data,
    )


@router.get(
    "/{vendor_id}/shipping-tiers",
    response_model=StandardResponse[ShippingTier],
    summary="Get shipping tiers for a vendor",
    description="Returns a list of shipping tiers associated with the specified vendor ID.",
)
def get_vendor_shipping_tier(
    request: Request,
    vendor_id: int = Path(
        ..., description="Vendor ID associated with the shipping tiers"
    ),
    _api_key: str = Depends(verify_api_key),
) -> StandardResponse[ShippingTier]:
    """Retrieves all shipping tiers associated with a given vendor.

    Args:
        request (Request): The request instance.
        vendor_id (int): Vendor ID associated with the shipping tiers.
        _api_key (str): API key for authorization.

    Returns:
        StandardResponse[ShippingTier]: Standard response containing a list of shipping tiers for the vendor.
    """
    logger = logging.getLogger("api.vendors.shipping_tiers")
    vendor_ids = {1, 2, 3, 4, 5, 6}
    if vendor_id not in vendor_ids:
        logger.error("Vendor ID doesn't exist.", extra={"vendor_id": vendor_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found.",
        )

    raw_data = request.app.state.shipping_tiers_by_vendor.get(vendor_id, [])
    vendors = TypeAdapter(List[ShippingTier])
    data = vendors.validate_python(raw_data)
    return StandardResponse(
        status="success",
        code=status.HTTP_200_OK,
        message=f"Queried {len(data)} shipping tier data for vendor {vendor_id}.",
        data=data,
    )
