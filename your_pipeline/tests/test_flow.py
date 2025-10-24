from pathlib import Path
from tempfile import TemporaryDirectory
import math
import os

import pytest
from sqlalchemy import select

import your_pipeline.flows.repricing_flow as flows
from your_pipeline.db.repo import Database
from your_pipeline.db.models import RepricedProduct

# keep Prefect quiet during tests
os.environ.setdefault("PREFECT_LOGGING_LEVEL", "ERROR")
os.environ.setdefault("PREFECT_LOGGING_TO_CONSOLE", "0")


class FakeApiClient:
    def __init__(self): ...
    def close(self): ...

    def get_vendors(self):
        return [
            {"vendor_id": 1, "name": "Titan Labs"},
            {"vendor_id": 2, "name": "Prime Distributors"},
        ]

    def get_brands(self, vendor_id: int):
        return [{"brand_id": 10, "name": "StoneBridge"}] if vendor_id == 2 else []

    def get_categories(self, vendor_id: int):
        return [
            {"category_id": 20, "name": "Electronics"},
            {"category_id": 21, "name": "Toys & Kids"},
        ]

    def get_shipping_tiers(self, vendor_id: int):
        return [{"shipping_tier_id": 30, "shipping_tier": "STD", "shipping_cost": 15.0}]

    def get_products(self, vendor_id: int):
        if vendor_id == 1:  # Titan Labs
            return [
                {"sku": "TL-E-1", "name": "Gadget", "cost": 100.0,
                 "brand_id": None, "category_id": 20, "shipping_tier_id": 30},  # VC path
                {"sku": "TL-TK-1", "name": "Toy", "cost": 50.0,
                 "brand_id": None, "category_id": 21, "shipping_tier_id": 30},  # category path
            ]
        if vendor_id == 2:  # Prime Distributors
            return [
                {"sku": "PD-BRAND-1", "name": "Headphones", "cost": 80.0,
                 "brand_id": 10, "category_id": 20, "shipping_tier_id": None},  # brand path
            ]
        return []


def fake_rules_loader():
    return {
        "vendor_rules": {
            "titan labs": {"extra_cost": 20, "target_margin": 0.20},
            "prime distributors": {"extra_cost": 10, "target_margin": 0.15},
        },
        "category_rules": {
            "electronics": 0.35,
            "toys & kids": 0.25,
        },
        "vendor_category_rules": {
            "titan labs": {
                "electronics": {"target_margin": 0.40, "adjustment_type": "delta", "adjustment_value": -10}
            }
        },
        "brand_rules": {
            "stonebridge": 0.60,
        },
        "default_target_margin": 0.12,
    }


class PatchedDatabase:
    """Proxy Database to a temp SQLite URL and keep track of created engines."""
    instances = []

    def __init__(self, db_url: str | None = None):
        from your_pipeline.db.repo import Database as RealDB
        self._db = RealDB(db_url=self.__class__._DB_URL)
        self.__class__.instances.append(self._db)

    def __getattr__(self, name):
        return getattr(self._db, name)


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_repricing_flow_e2e(monkeypatch):
    with TemporaryDirectory() as td:
        db_url = f"sqlite:///{Path(td) / 'prefect_flow.db'}"

        # patch flow dependencies
        monkeypatch.setattr(flows, "ApiClient", FakeApiClient)
        monkeypatch.setattr(flows.rules_loader, "load_all_rules", fake_rules_loader)
        PatchedDatabase._DB_URL = db_url
        monkeypatch.setattr(flows, "Database", PatchedDatabase)

        # run the flow
        flows.repricing_flow()

        # release SQLite handles created inside the flow
        for inst in list(PatchedDatabase.instances):
            inst.dispose()

        # assert results
        db = Database(db_url=db_url)
        try:
            with db.session() as s:
                rows = s.execute(select(RepricedProduct)).scalars().all()
            got = {r.sku: r for r in rows}
            assert set(got) == {"TL-E-1", "TL-TK-1", "PD-BRAND-1"}

            assert got["TL-E-1"].rule_source == "vendor_category"
            assert math.isclose(got["TL-E-1"].target_margin_used, 0.40)
            assert math.isclose(got["TL-E-1"].vendor_extra_cost_applied, 10.0)

            assert got["TL-TK-1"].rule_source == "category"
            assert math.isclose(got["TL-TK-1"].target_margin_used, 0.25)
            assert math.isclose(got["TL-TK-1"].vendor_extra_cost_applied, 20.0)

            assert got["PD-BRAND-1"].rule_source == "brand"
            assert math.isclose(got["PD-BRAND-1"].target_margin_used, 0.60)
        finally:
            db.dispose()
