from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Tuple, Type, List

from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from your_pipeline.config.settings import settings
from your_pipeline.clients.api_client import ApiClient
from your_pipeline.db.repo import Database
from your_pipeline.pricing import rules_loader
from your_pipeline.pricing.engine import compute_price
from your_pipeline.models import ProductIn, RuleContext, VendorRule, VCOverride

from your_pipeline.db.models import (
    Product,
    Vendor,
    Brand,
    Category,
    ShippingTier,
    RepricedProduct,
)


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return s.strip().replace("’", "'").replace("＆", "&").casefold()

def _rules_to_ctx(rules: Dict[str, Any]) -> RuleContext:
    vendor_rules = {_norm(k): VendorRule(**v) for k, v in rules["vendor_rules"].items()}
    vc_rules: Dict[str, Dict[str, VCOverride]] = {
        _norm(vn): {_norm(cat): VCOverride(**spec) for cat, spec in cats.items()}
        for vn, cats in rules["vendor_category_rules"].items()
    }
    return RuleContext(
        vendor_rules=vendor_rules,
        category_rules={_norm(k): float(v) for k, v in rules["category_rules"].items()},
        vendor_category_rules=vc_rules,
        brand_rules={_norm(k): float(v) for k, v in rules.get("brand_rules", {}).items()},
        default_target_margin=float(rules.get("default_target_margin", 0.12)),
    )

def _db() -> Database:
    db_url = getattr(settings, "DATABASE_URL", getattr(settings, "db_url", None))
    if not db_url:
        raise RuntimeError("No database URL found (settings.DATABASE_URL or settings.db_url).")
    print(f"[flow] using DB -> {db_url}")
    return Database(db_url=db_url)

def _engine():
    db_url = getattr(settings, "DATABASE_URL", getattr(settings, "db_url", None))
    if not db_url:
        raise RuntimeError("No database URL found (settings.DATABASE_URL or settings.db_url).")
    return create_engine(db_url, future=True)

def _first_attr(obj: Any, names: Iterable[str]) -> Any:
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None

def _pick_str(obj: Any, names: Iterable[str]) -> Optional[str]:
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if isinstance(v, str) and v.strip():
                return v
    return None

def _get_vendor_rel(p: Product) -> Optional[Vendor]:
    return _first_attr(p, ("vendor", "Vendor", "vendor_ref", "vendor_obj"))

def _get_brand_rel(p: Product) -> Optional[Brand]:
    return _first_attr(p, ("brand", "Brand", "brand_ref", "brand_obj"))

def _get_category_rel(p: Product) -> Optional[Category]:
    return _first_attr(p, ("category", "Category", "category_ref", "category_obj"))

def _get_shipping_tier_rel(p: Product) -> Optional[ShippingTier]:
    return _first_attr(p, ("shipping_tier", "ShippingTier", "tier", "Tier"))

def _first_pk_column(model: Type[Any]):
    for cand in ("id", "ID", "pk"):
        if hasattr(model, cand):
            return getattr(model, cand)
    return getattr(model, "sku")

def _lookup_by_id(session: Session, model: Type[Any], id_val: Any) -> Optional[Any]:
    if id_val is None:
        return None
    try:
        obj = session.get(model, id_val)
        if obj is not None:
            return obj
    except Exception:
        pass
    try:
        return session.execute(select(model).where(_first_pk_column(model) == id_val)).scalars().first()
    except Exception:
        return None

def _shipping_cost_from_product(p: Product) -> Optional[float]:
    for name in ("shipping_cost", "shipping_tier_cost", "ship_cost", "shipping_fee"):
        if hasattr(p, name):
            val = getattr(p, name)
            if val is not None:
                try:
                    return float(val)
                except Exception:
                    pass
    return None

def _shipping_cost_from_tier(st: Optional[ShippingTier]) -> Optional[float]:
    if not st:
        return None
    for name in ("shipping_cost", "cost", "price"):
        if hasattr(st, name):
            try:
                return float(getattr(st, name))
            except Exception:
                pass
    return None

def _safe_name(raw: Optional[str]) -> str:
    n = _norm(raw) if raw is not None else None
    return n if n else "unknown"

def _extract_names(session: Session, p: Product) -> Tuple[str, str, str]:
    vendor_raw = _pick_str(p, ("vendor_name", "vendor", "supplier", "vendor_str"))
    brand_raw  = _pick_str(p, ("brand_name", "brand", "brand_str", "manufacturer", "maker"))
    cat_raw    = _pick_str(p, ("category_name", "category", "category_str", "category_title"))

    if not vendor_raw:
        ven = _get_vendor_rel(p)
        vendor_raw = getattr(ven, "name", None) if ven else None
    if not brand_raw:
        br = _get_brand_rel(p)
        brand_raw = getattr(br, "name", None) if br else None
    if not cat_raw:
        cat = _get_category_rel(p)
        cat_raw = getattr(cat, "name", None) if cat else None

    if not vendor_raw:
        vid = _first_attr(p, ("vendor_id", "vendorID", "vendorPk"))
        ven = _lookup_by_id(session, Vendor, vid)
        vendor_raw = getattr(ven, "name", None) if ven else None
    if not brand_raw:
        bid = _first_attr(p, ("brand_id", "brandID", "brandPk"))
        br = _lookup_by_id(session, Brand, bid)
        brand_raw = getattr(br, "name", None) if br else None
    if not cat_raw:
        cid = _first_attr(p, ("category_id", "categoryID", "categoryPk"))
        cat = _lookup_by_id(session, Category, cid)
        cat_raw = getattr(cat, "name", None) if cat else None

    return (_safe_name(vendor_raw), _safe_name(brand_raw), _safe_name(cat_raw))

def _to_productin(session: Session, p: Product) -> ProductIn:
    vendor_name, brand_name, category_name = _extract_names(session, p)
    shipping_cost = _shipping_cost_from_product(p)
    if shipping_cost is None:
        shipping_cost = _shipping_cost_from_tier(_get_shipping_tier_rel(p))
    return ProductIn(
        sku=p.sku,
        vendor_name=vendor_name,
        brand_name=brand_name,
        category_name=category_name,
        cost=float(p.cost),
        shipping_cost=shipping_cost,
    )

def _to_repr_dict(sku: str, out: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sku": sku,
        "computed_price": float(out["computed_price"]),
        "target_margin_used": float(out["target_margin_used"]),
        "total_cost": float(out["total_cost"]),
        "vendor_extra_cost_applied": float(out["vendor_extra_cost_applied"]),
        "rule_source": str(out["rule_source"]),
    }

def _upsert_batch_with_orm(session: Session, batch: List[Dict[str, Any]]) -> None:
    for row in batch:
        sku = row.pop("sku")
        rp = session.get(RepricedProduct, sku)
        if rp is None:
            rp = RepricedProduct(sku=sku)
            session.add(rp)
        rp.computed_price = row["computed_price"]
        rp.target_margin_used = row["target_margin_used"]
        rp.total_cost = row["total_cost"]
        rp.vendor_extra_cost_applied = row["vendor_extra_cost_applied"]
        rp.rule_source = row["rule_source"]


@task(retries=2, retry_delay_seconds=5, log_prints=True)
def extract_all() -> Dict[str, Any]:
    print("[flow] extracting from API…")
    api = ApiClient()
    try:
        vendors = api.get_vendors()
        per_vendor: Dict[str, Any] = {}
        for v in vendors:
            vid = v.get("vendor_id", v.get("id"))
            per_vendor[str(vid)] = {
                "vendor": v,
                "brands": api.get_brands(vid),
                "categories": api.get_categories(vid),
                "shipping_tiers": api.get_shipping_tiers(vid),
                "products": api.get_products(vid),
            }
        print(f"[flow] extracted vendors={len(vendors)}")
        return {"vendors": vendors, "per_vendor": per_vendor}
    finally:
        api.close()

@task(cache_policy=NO_CACHE, log_prints=True)
def load_dim_tables(extracted: Dict[str, Any]) -> None:
    print("[flow] loading vendors/brands/categories/shipping_tiers…")
    db = _db()
    vendors = [{"vendor_id": v.get("vendor_id", v.get("id")), "name": v["name"]} for v in extracted["vendors"]]
    db.upsert_vendors(vendors)
    tb, tc, tt = 0, 0, 0
    for vid_key, bundle in extracted["per_vendor"].items():
        vid = int(vid_key)
        brands = [{"brand_id": b["brand_id"], "vendor_id": vid, "name": b["name"]} for b in bundle["brands"]]
        cats   = [{"category_id": c["category_id"], "vendor_id": vid, "name": c["name"]} for c in bundle["categories"]]
        tiers  = [{
            "shipping_tier_id": t["shipping_tier_id"],
            "vendor_id": vid,
            "name": t.get("shipping_tier"),
            "shipping_cost": float(t.get("shipping_cost", 0)),
        } for t in bundle["shipping_tiers"]]
        db.upsert_brands(brands);        tb += len(brands)
        db.upsert_categories(cats);      tc += len(cats)
        db.upsert_shipping_tiers(tiers); tt += len(tiers)
    print(f"[flow] dims loaded -> vendors:{len(vendors)} brands:{tb} categories:{tc} tiers:{tt}")

@task(cache_policy=NO_CACHE, log_prints=True)
def load_products_only(extracted: Dict[str, Any]) -> int:
    print("[flow] loading products only (no repricing yet)…")
    db = _db()
    raw_rows: List[Dict[str, Any]] = []
    for vid_key, bundle in extracted["per_vendor"].items():
        for p in bundle["products"]:
            raw_rows.append({
                "sku": p["sku"],
                "vendor_id": int(vid_key),
                "name": p.get("name"),
                "cost": float(p["cost"]),
                "brand_id": p.get("brand_id"),
                "category_id": p.get("category_id"),
                "shipping_tier_id": p.get("shipping_tier_id"),
            })
    db.upsert_products(raw_rows)
    print(f"[flow] loaded {len(raw_rows)} products.")
    return len(raw_rows)

@task(cache_policy=NO_CACHE, log_prints=True)
def reprice_from_db(rules_ctx: RuleContext, limit: Optional[int] = None, commit_every: int = 200) -> int:
    print("[flow] recomputing prices from DB rows and upserting repriced_products…")
    eng = _engine()
    updated = 0
    total = 0
    with Session(eng) as s:
        sel = select(Product).order_by(Product.sku)
        if limit:
            sel = sel.limit(limit)
        products: List[Product] = s.scalars(sel).all()
        print(f"[flow] will reprice {len(products)} products…")
        batch: List[Dict[str, Any]] = []
        for p in products:
            total += 1
            pi = _to_productin(s, p)
            out = compute_price(pi, rules_ctx)
            out_dict = out.model_dump() if hasattr(out, "model_dump") else {
                "computed_price": float(getattr(out, "computed_price")),
                "target_margin_used": float(getattr(out, "target_margin_used")),
                "total_cost": float(getattr(out, "total_cost")),
                "vendor_extra_cost_applied": float(getattr(out, "vendor_extra_cost_applied")),
                "rule_source": str(getattr(out, "rule_source")),
            }
            batch.append(_to_repr_dict(p.sku, out_dict))
            if len(batch) >= commit_every:
                _upsert_batch_with_orm(s, batch)
                s.commit()
                updated += len(batch)
                batch.clear()
        if batch:
            _upsert_batch_with_orm(s, batch)
            s.commit()
            updated += len(batch)
    print(f"[flow] repriced {total} products; updated {updated} rows.")
    return updated


@flow(name="repricing_flow", log_prints=True)
def repricing_flow(limit: Optional[int] = None, commit_every: int = 200) -> None:
    log = get_run_logger()
    rules_ctx = _rules_to_ctx(rules_loader.load_all_rules())
    extracted = extract_all()
    load_dim_tables(extracted)
    load_products_only(extracted)
    reprice_from_db(rules_ctx, limit=limit, commit_every=commit_every)
    log.info("Done.")

if __name__ == "__main__":
    repricing_flow()
