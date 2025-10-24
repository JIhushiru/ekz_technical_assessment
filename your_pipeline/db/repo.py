from __future__ import annotations
from typing import Iterable, Mapping, List
from contextlib import contextmanager

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from your_pipeline.config.settings import settings
from .models import Base, Vendor, Brand, Category, ShippingTier, Product, RepricedProduct


def _chunked(seq: List[Mapping], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


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
    def upsert_vendors(self, rows: Iterable[Mapping], batch_size: int = 200):
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(Vendor).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Vendor.vendor_id],
                set_={"name": stmt.excluded.name},
            )
            with self.session() as s:
                s.execute(stmt)

    def upsert_brands(self, rows: Iterable[Mapping], batch_size: int = 200):
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(Brand).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Brand.brand_id],
                set_={"vendor_id": stmt.excluded.vendor_id, "name": stmt.excluded.name},
            )
            with self.session() as s:
                s.execute(stmt)

    def upsert_categories(self, rows: Iterable[Mapping], batch_size: int = 200):
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(Category).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Category.category_id],
                set_={"vendor_id": stmt.excluded.vendor_id, "name": stmt.excluded.name},
            )
            with self.session() as s:
                s.execute(stmt)

    def upsert_shipping_tiers(self, rows: Iterable[Mapping], batch_size: int = 200):
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(ShippingTier).values(chunk)
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

    def upsert_products(self, rows: Iterable[Mapping], batch_size: int = 120):
        """
        Products have 7 cols -> 999 // 7 ≈ 142; keep a safe margin (120) per batch.
        """
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(Product).values(chunk)
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

    def upsert_repricings(self, rows: Iterable[Mapping], batch_size: int = 160):
        """
        Repricings have 6 cols -> 999 // 6 ≈ 166; use 160 to be safe.
        """
        data = list(rows)
        for chunk in _chunked(data, batch_size):
            stmt = sqlite_insert(RepricedProduct).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[RepricedProduct.sku],
                set_={
                    "computed_price": stmt.excluded.computed_price,
                    "target_margin_used": stmt.excluded.target_margin_used,
                    "total_cost": stmt.excluded.total_cost,
                    "vendor_extra_cost_applied": stmt.excluded.vendor_extra_cost_applied,
                    "rule_source": stmt.excluded.rule_source,
                    "computed_at": func.current_timestamp(),
                },
            )
            with self.session() as s:
                s.execute(stmt)

    def dispose(self):
        self.engine.dispose()
