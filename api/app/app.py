import json
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

import api.utils.load_env  # noqa
from api.app.config.settings import setup_logging
from api.utils.file_loader import load_grouped_data, load_data
from api.app.routers import vendor, product, category, brand


setup_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger = logging.getLogger("api.lifespan")
    application.state.vendors = load_data("./api/data/vendor_id_data.json")  # type: ignore

    # Grouped data
    application.state.shipping_tiers_by_vendor = load_grouped_data(  # type: ignore
        "./api/data/vendor_shipping_data.json"
    )
    application.state.products_by_vendor = load_grouped_data("./api/data/final_sample_data.json")  # type: ignore
    application.state.categories_by_vendor = load_grouped_data("./api/data/vendor_category_data.json")  # type: ignore
    application.state.brands_by_vendor = load_grouped_data("./api/data/vendor_brand_data.json")  # type: ignore

    # Debug print examples
    evergreen_tier = json.dumps(application.state.shipping_tiers_by_vendor.get(1), indent=4)  # type: ignore
    evergreen_cat = json.dumps(application.state.categories_by_vendor.get(1), indent=4)  # type: ignore
    evergreen_brand = json.dumps(application.state.brands_by_vendor.get(1), indent=4)  # type: ignore
    logger.debug(f"Shipping Tiers for Vendor 1: {evergreen_tier}")
    logger.debug(f"Categories for Vendor 1: {evergreen_cat}")
    logger.debug(f"Brands for Vendor 1: {evergreen_brand}")
    yield


description = """
This API provides access to simulated data for vendors, products, brands, categories, and shipping tiers.  
**It is intended solely for the technical assessment and should not be modified or used in production.**

## Available Endpoints
- `GET /api/v1/vendors/` - Retrieve all vendors
- `GET /api/v1/vendors/{vendor_id}/shipping-tiers` - Get shipping tiers for a vendor
- `GET /api/v1/products/` - Get products filtered by vendor
- `GET /api/v1/categories/` - Get categories filtered by vendor
- `GET /api/v1/brands/` - Get brands filtered by vendor

*Note: All endpoints require a valid API key.*
"""
app = FastAPI(
    title="EKZ Technical Assessment", description=description, lifespan=lifespan
)
app.include_router(router=vendor.router)
app.include_router(router=product.router)
app.include_router(router=category.router)
app.include_router(router=brand.router)
