from __future__ import annotations

import argparse
from typing import Any, Dict, Iterable, Optional, Tuple, Type, List
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from your_pipeline.config.settings import settings
from your_pipeline.pricing import rules_loader
from your_pipeline.pricing.engine import compute_price
from your_pipeline.models import ProductIn, RuleContext, VendorRule, VCOverride
from your_pipeline.db.models import Product, Vendor, Brand, Category, ShippingTier, RepricedProduct

# rules / context 
def _norm(s: Optional[str]) -> Optional[str]:
    if s is None: return None
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

def _build_ctx() -> RuleContext:
    return _rules_to_ctx(rules_loader.load_all_rules())

# getters
def _first_attr(obj: Any, names: Iterable[str]) -> Any:
    for n in names:
        if hasattr(obj, n): return getattr(obj, n)
    return None

def _pick_str(obj: Any, names: Iterable[str]) -> Optional[str]:
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if isinstance(v, str) and v.strip(): return v
    return None

def _get_vendor_rel(p: Product) -> Optional[Vendor]:   return _first_attr(p, ("vendor", "Vendor"))
def _get_brand_rel(p: Product) -> Optional[Brand]:     return _first_attr(p, ("brand", "Brand"))
def _get_category_rel(p: Product) -> Optional[Category]: return _first_attr(p, ("category", "Category"))
def _get_shipping_tier_rel(p: Product) -> Optional[ShippingTier]: return _first_attr(p, ("shipping_tier", "ShippingTier", "tier", "Tier"))

def _first_pk_column(model: Type[Any]):
    for cand in ("id", "ID", "pk"):
        if hasattr(model, cand): return getattr(model, cand)
    return getattr(model, "sku")

def _lookup_by_id(session: Session, model: Type[Any], id_val: Any) -> Optional[Any]:
    if id_val is None: return None
    try:
        obj = session.get(model, id_val)
        if obj is not None: return obj
    except Exception:
        pass
    try:
        return session.execute(select(model).where(_first_pk_column(model) == id_val)).scalars().first()
    except Exception:
        return None

# product -> ProductIn
def _shipping_cost_from_product(p: Product) -> Optional[float]:
    for name in ("shipping_cost", "shipping_tier_cost", "ship_cost", "shipping_fee"):
        if hasattr(p, name):
            val = getattr(p, name)
            if val is not None:
                try: return float(val)
                except Exception: pass
    return None

def _shipping_cost_from_tier(st: Optional[ShippingTier]) -> Optional[float]:
    if not st: return None
    for name in ("shipping_cost", "cost", "price"):
        if hasattr(st, name):
            try: return float(getattr(st, name))
            except Exception: pass
    return None

def _safe_name(raw: Optional[str]) -> str:
    n = _norm(raw) if raw is not None else None
    return n if n else "unknown"

def _extract_names(session: Session, p: Product) -> Tuple[str, str, str]:
    vendor_raw = _pick_str(p, ("vendor_name", "vendor", "supplier", "vendor_str"))
    brand_raw  = _pick_str(p, ("brand_name", "brand", "brand_str", "manufacturer", "maker"))
    cat_raw    = _pick_str(p, ("category_name", "category", "category_str", "category_title"))

    if not vendor_raw:
        ven = _get_vendor_rel(p); vendor_raw = getattr(ven, "name", None) if ven else None
    if not brand_raw:
        br = _get_brand_rel(p);  brand_raw  = getattr(br, "name", None) if br else None
    if not cat_raw:
        cat = _get_category_rel(p); cat_raw = getattr(cat, "name", None) if cat else None

    if not vendor_raw:
        vid = _first_attr(p, ("vendor_id", "vendorID", "vendorPk"))
        ven = _lookup_by_id(session, Vendor, vid); vendor_raw = getattr(ven, "name", None) if ven else None
    if not brand_raw:
        bid = _first_attr(p, ("brand_id", "brandID", "brandPk"))
        br = _lookup_by_id(session, Brand, bid);  brand_raw  = getattr(br, "name", None) if br else None
    if not cat_raw:
        cid = _first_attr(p, ("category_id", "categoryID", "categoryPk"))
        cat = _lookup_by_id(session, Category, cid); cat_raw = getattr(cat, "name", None) if cat else None

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

# compute + compare 
def _out_to_dict(out: Any) -> Dict[str, Any]:
    if hasattr(out, "model_dump"):
        out = out.model_dump()
    if isinstance(out, dict):
        return {
            "computed_price": float(out["computed_price"]),
            "target_margin_used": float(out["target_margin_used"]),
            "total_cost": float(out["total_cost"]),
            "vendor_extra_cost_applied": float(out["vendor_extra_cost_applied"]),
            "rule_source": str(out["rule_source"]),
        }
    return {
        "computed_price": float(getattr(out, "computed_price")),
        "target_margin_used": float(getattr(out, "target_margin_used")),
        "total_cost": float(getattr(out, "total_cost")),
        "vendor_extra_cost_applied": float(getattr(out, "vendor_extra_cost_applied")),
        "rule_source": str(getattr(out, "rule_source")),
    }

def _eq_money(a: float, b: float) -> bool:  return f"{a:.2f}" == f"{b:.2f}"
def _eq_margin(a: float, b: float) -> bool: return f"{a:.4f}" == f"{b:.4f}"

def _get_saved_repriced(session: Session, sku: str) -> Optional[RepricedProduct]:
    try:
        rp = session.get(RepricedProduct, sku)
        if rp is not None: return rp
    except Exception:
        pass
    try:
        return session.execute(select(RepricedProduct).filter_by(sku=sku)).scalars().first()
    except Exception:
        return None

def main(limit: Optional[int], explain: Optional[List[str]], ignore_missing: bool, stats: bool, peek: bool) -> int:
    db_url = getattr(settings, "DATABASE_URL", getattr(settings, "db_url", None))
    if not db_url:
        raise RuntimeError("No database URL found (DATABASE_URL or db_url).")
    engine = create_engine(db_url, future=True)
    ctx = _build_ctx()

    explain_set = set(explain or [])
    mismatches = missing = compared = 0
    seen_default = seen_vendor = seen_category = seen_brand = seen_vc = 0

    with Session(engine) as s:
        sel = select(Product).order_by(Product.sku)
        if limit: sel = sel.limit(limit)
        products: List[Product] = s.scalars(sel).all()
        print(f"[verify] comparing {len(products)} products...")

        if peek:
            print("[peek] first 10 (vendor | category | brand):")
            for p in products[:10]:
                v, b, c = _extract_names(s, p)
                print(f"  {v} | {c} | {b}")

        for p in products:
            compared += 1
            pin = _to_productin(s, p)
            out = _out_to_dict(compute_price(pin, ctx))

            rs = out["rule_source"]
            if rs == "default": seen_default += 1
            elif rs == "vendor": seen_vendor += 1
            elif rs == "category": seen_category += 1
            elif rs == "brand": seen_brand += 1
            elif rs == "vendor_category": seen_vc += 1

            saved = _get_saved_repriced(s, p.sku)
            if saved is None:
                missing += 1
                if not ignore_missing:
                    mismatches += 1
                    print(f"  SKU={pin.sku}\n    recomputed: {out}\n    stored    : <missing repriced row>")
                continue

            stored = {
                "computed_price": float(saved.computed_price),
                "target_margin_used": float(saved.target_margin_used),
                "total_cost": float(saved.total_cost),
                "vendor_extra_cost_applied": float(saved.vendor_extra_cost_applied),
                "rule_source": str(saved.rule_source),
            }

            if p.sku in explain_set:
                print(f"[explain:{p.sku}] vendor={pin.vendor_name} category={pin.category_name} brand={pin.brand_name}")
                print("    out   :", out)
                print("    saved :", stored)

            ok_price = _eq_money(out["computed_price"], stored["computed_price"])
            ok_tm    = _eq_margin(out["target_margin_used"], stored["target_margin_used"])
            ok_tc    = _eq_money(out["total_cost"], stored["total_cost"])
            ok_extra = _eq_money(out["vendor_extra_cost_applied"], stored["vendor_extra_cost_applied"])
            ok_rule  = out["rule_source"] == stored["rule_source"]

            if not (ok_price and ok_tm and ok_tc and ok_extra and ok_rule):
                mismatches += 1
                print(f"  SKU={pin.sku}\n    recomputed: {out}\n    stored    : {stored}")

    print(f"[verify] compared {compared} products, mismatches: {mismatches}", end="")
    if missing: print(f" (missing repriced rows: {missing})")
    else: print()

    if stats:
        print(f"[verify] rule_source counts -> default:{seen_default} vendor:{seen_vendor} category:{seen_category} brand:{seen_brand} vendor_category:{seen_vc}")

    if mismatches:
        print("[verify] FAIL: repricing differences detected.")
        return 1
    print("[verify] OK: no repricing differences.")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--explain", nargs="*")
    ap.add_argument("--ignore-missing", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--peek", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.limit, args.explain, args.ignore_missing, args.stats, args.peek))
