from __future__ import annotations
from typing import Iterable, Mapping
from contextlib import contextmanager

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from your_pipeline.config.settings import settings
from .models import Base, Vendor, Brand, Category, ShippingTier, Product, RepricedProduct


class Database:
    def __init__(self, db_url: str | None = None):
        self.engine = create_engine(db_url or settings.db_url, future=True)
        self.Session = sessionmaker(self.engine, expire_on_commit=False, future=True)
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
        s = self.Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # upserts
    def upsert_vendors(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(Vendor).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[Vendor.vendor_id],
            set_={"name": stmt.excluded.name},
        )
        with self.session() as s:
            s.execute(stmt)

    def upsert_brands(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(Brand).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[Brand.brand_id],
            set_={
                "vendor_id": stmt.excluded.vendor_id,
                "name": stmt.excluded.name,
            },
        )
        with self.session() as s:
            s.execute(stmt)

    def upsert_categories(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(Category).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[Category.category_id],
            set_={
                "vendor_id": stmt.excluded.vendor_id,
                "name": stmt.excluded.name,
            },
        )
        with self.session() as s:
            s.execute(stmt)

    def upsert_shipping_tiers(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(ShippingTier).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[ShippingTier.shipping_tier_id],
            set_={
                "vendor_id": stmt.excluded.vendor_id,
                "name": stmt.excluded.name,
                "shipping_cost": stmt.excluded.shipping_cost,
            },
        )
        with self.session() as s:
            s.execute(stmt)

    def upsert_products(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(Product).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[Product.sku],
            set_={
                "vendor_id": stmt.excluded.vendor_id,
                "name": stmt.excluded.name,
                "cost": stmt.excluded.cost,
                "brand_id": stmt.excluded.brand_id,
                "category_id": stmt.excluded.category_id,
                "shipping_tier_id": stmt.excluded.shipping_tier_id,
            },
        )
        with self.session() as s:
            s.execute(stmt)

    def upsert_repricings(self, rows: Iterable[Mapping]):
        stmt = sqlite_insert(RepricedProduct).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=[RepricedProduct.sku],
            set_={
                "computed_price": stmt.excluded.computed_price,
                "target_margin_used": stmt.excluded.target_margin_used,
                "total_cost": stmt.excluded.total_cost,
                "vendor_extra_cost_applied": stmt.excluded.vendor_extra_cost_applied,
                "rule_source": stmt.excluded.rule_source,
                # refresh the timestamp on every update
                "computed_at": func.current_timestamp(),
            },
        )
        with self.session() as s:
            s.execute(stmt)

    def dispose(self):
        """Release SQLite file handles (Windows needs this for temp file cleanup)."""
        self.engine.dispose()
