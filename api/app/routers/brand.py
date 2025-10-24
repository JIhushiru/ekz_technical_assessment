from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import TypeAdapter

from api.app.auth.dependencies import verify_api_key
from api.app.models.brand import Brand
from api.app.models.response import StandardResponse

router = APIRouter(
    prefix="/api/v1/brands",
    tags=["brands"],
    responses={404: {"description": "Not Found"}},
)


@router.get(
    "/",
    response_model=StandardResponse[Brand],
    summary="Get brands filtered by vendor",
    description="Returns a list of brands filtered by the specified vendor ID.",
)
def get_brand_by_vendor(
    request: Request,
    vendor_id: int = Query(..., description="ID of the vendor to filter brands by"),
    _api_key: str = Depends(verify_api_key),
) -> StandardResponse[Brand]:
    """Retrieves brands associated with a specific vendor.

    Args:
        vendor_id (int): Vendor ID to filter brands by.
        request (Request): The request instance.
        _api_key (str): API key for authorization.

    Returns:
        StandardResponse[Brand]: Standard response containing a list of brands for the vendor.
    """
    logger = logging.getLogger("api.brands")
    vendor_ids = {1, 2, 3, 4, 5, 6}
    if vendor_id not in vendor_ids:
        logger.error("Vendor ID doesn't exist.", extra={"vendor_id": vendor_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found.",
        )

    raw_data = request.app.state.brands_by_vendor.get(vendor_id, [])
    brands = TypeAdapter(List[Brand])
    data = brands.validate_python(raw_data)
    return StandardResponse(
        status="success",
        code=status.HTTP_200_OK,
        message=f"Queried {len(data)} brands for vendor {vendor_id}.",
        data=data,
    )
