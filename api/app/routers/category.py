from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import TypeAdapter

from api.app.auth.dependencies import verify_api_key
from api.app.models.category import Category
from api.app.models.response import StandardResponse

router = APIRouter(
    prefix="/api/v1/categories",
    tags=["categories"],
    responses={404: {"description": "Not Found"}},
)


@router.get(
    "/",
    response_model=StandardResponse[Category],
    summary="Get categories filtered by vendor",
    description="Returns a list of categories filtered by the specified vendor ID.",
)
def get_categories_by_vendor(
    request: Request,
    vendor_id: int = Query(..., description="ID of the vendor to filter categories by"),
    _api_key: str = Depends(verify_api_key),
) -> StandardResponse[Category]:
    """
    Retrieves categories associated with a specific vendor.

    Args:
        vendor_id (int): Vendor ID to filter categories by.
        request (Request): The request instance.
        _api_key (str): API key for authorization.

    Returns:
        StandardResponse[Category]: Standard response containing a list of categories for the vendor.
    """
    logger = logging.getLogger("api.categories")
    vendor_ids = {1, 2, 3, 4, 5, 6}
    if vendor_id not in vendor_ids:
        logger.error("Vendor ID doesn't exist.", extra={"vendor_id": vendor_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found.",
        )

    raw_data = request.app.state.categories_by_vendor.get(vendor_id, [])
    categories = TypeAdapter(List[Category])
    data = categories.validate_python(raw_data)
    return StandardResponse(
        status="success",
        code=status.HTTP_200_OK,
        message=f"Queried {len(data)} categories for vendor {vendor_id}.",
        data=data,
    )
