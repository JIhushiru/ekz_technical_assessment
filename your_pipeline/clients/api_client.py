from typing import Any, Dict, List, Optional
import httpx
from your_pipeline.config.settings import settings

class ApiClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-KEY": self.api_key},
            timeout=30,
            follow_redirects=True,
        )

    def close(self):
        self._client.close()

    # /vendors/
    def get_vendors(self) -> List[Dict[str, Any]]:
        r = self._client.get("/vendors/")  # trailing slash
        r.raise_for_status()
        return r.json()["data"]

    # /products?vendor_id=...
    def get_products(self, vendor_id: int) -> List[Dict[str, Any]]:
        r = self._client.get("/products", params={"vendor_id": vendor_id})
        r.raise_for_status()
        return r.json()["data"]

    # /categories?vendor_id=...
    def get_categories(self, vendor_id: int) -> List[Dict[str, Any]]:
        r = self._client.get("/categories", params={"vendor_id": vendor_id})
        r.raise_for_status()
        return r.json()["data"]

    # /brands?vendor_id=...
    def get_brands(self, vendor_id: int) -> List[Dict[str, Any]]:
        r = self._client.get("/brands", params={"vendor_id": vendor_id})
        r.raise_for_status()
        return r.json()["data"]

    # /vendors/{vendor_id}/shipping-tiers
    def get_shipping_tiers(self, vendor_id: int) -> List[Dict[str, Any]]:
        r = self._client.get(f"/vendors/{vendor_id}/shipping-tiers")
        r.raise_for_status()
        return r.json()["data"]
