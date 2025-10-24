from typing import Any, Dict, List

import pytest
import your_pipeline.flows.repricing_flow as flows


class FakeApiClient:
    def __init__(self):
        pass

    def close(self):
        pass

    def get_vendors(self) -> List[Dict[str, Any]]:
        return [{"vendor_id": 1, "name": "Titan Labs"}]

    def get_brands(self, vendor_id: int):
        assert vendor_id == 1
        return [{"brand_id": 10, "name": "StoneBridge"}]

    def get_categories(self, vendor_id: int):
        assert vendor_id == 1
        return [{"category_id": 20, "name": "Electronics"}]

    def get_shipping_tiers(self, vendor_id: int):
        assert vendor_id == 1
        return [{"shipping_tier_id": 30, "shipping_tier": "STD", "shipping_cost": 15.0}]

    def get_products(self, vendor_id: int):
        assert vendor_id == 1
        return [
            {
                "sku": "X-1",
                "name": "Gadget",
                "cost": 100.0,
                "brand_id": 10,
                "category_id": 20,
                "shipping_tier_id": 30,
            },
            {
                "sku": "X-2",
                "name": "Gizmo",
                "cost": 80.0,
                "brand_id": 10,
                "category_id": 20,
                "shipping_tier_id": None,
            },
        ]


def test_extract_all_maps_structure(monkeypatch):
    monkeypatch.setattr(flows, "ApiClient", FakeApiClient)

    out = flows.extract_all()
    assert "vendors" in out and "per_vendor" in out
    assert out["vendors"][0]["name"] == "Titan Labs"

    per = out["per_vendor"]["1"]
    assert per["brands"][0]["name"] == "StoneBridge"
    assert per["categories"][0]["name"] == "Electronics"
    assert per["shipping_tiers"][0]["shipping_cost"] == 15.0

    prods = per["products"]
    assert len(prods) == 2
    assert prods[0]["sku"] == "X-1"
    assert prods[1]["shipping_tier_id"] is None
