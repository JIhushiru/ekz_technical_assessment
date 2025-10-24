from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from your_pipeline.db.repo import Database
from your_pipeline.db.models import Vendor, RepricedProduct


def make_db(tmpdir: str) -> Database:
    db_url = f"sqlite:///{Path(tmpdir) / 'test.db'}"
    return Database(db_url=db_url)


def test_upsert_vendors_and_repricings_idempotent():
    with TemporaryDirectory() as td:
        db = make_db(td)
        try:
            # vendors
            db.upsert_vendors(
                [
                    {"vendor_id": 1, "name": "Titan Labs"},
                    {"vendor_id": 2, "name": "Prime Distributors"},
                ]
            )
            # update vendor name to confirm on_conflict update
            db.upsert_vendors([{"vendor_id": 2, "name": "Prime Distributors"}])

            with db.session() as s:
                names = [v.name for v in s.execute(select(Vendor)).scalars().all()]
            assert sorted(names) == ["Prime Distributors", "Titan Labs"]

            # repriced products (idempotent upsert)
            row1 = {
                "sku": "S-1",
                "computed_price": 199.45,
                "target_margin_used": 0.4,
                "total_cost": 120.0,
                "vendor_extra_cost_applied": 10.0,
                "rule_source": "vendor_category",
            }
            db.upsert_repricings([row1])

            # run again with changed price to ensure update + refresh timestamp
            row1b = dict(row1, computed_price=199.95)
            db.upsert_repricings([row1b])

            with db.session() as s:
                out = (
                    s.execute(
                        select(RepricedProduct).where(
                            RepricedProduct.sku == "S-1"
                        )
                    )
                    .scalar_one()
                )
                assert out.computed_price == 199.95
                assert out.rule_source == "vendor_category"
                assert out.target_margin_used == 0.4
                assert out.vendor_extra_cost_applied == 10.0
        finally:
            # Important for Windows: release SQLite file handle before temp cleanup
            db.dispose()
