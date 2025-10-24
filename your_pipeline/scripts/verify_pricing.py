"""
Verification script: recompute prices and compare with saved repriced_products.

Usage:
  python -m your_pipeline.scripts.verify_pricing
  python -m your_pipeline.scripts.verify_pricing --limit 500
"""

from typing import Optional, Dict, Any, List, Tuple
import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from your_pipeline.config.settings import settings
from your_pipeline.db.models import Vendor, Brand, Category, ShippingTier, Product, RepricedProduct
from your_pipeline.pricing.engine import compute_price
from your_pipeline.models import ProductIn, RuleContext
from your_pipeline.pricing.rules_loader import load_all_rules


def _rules_to_ctx(rules: Dict[str, Any]) -> RuleContext:
    # Convert dicts -> pydantic models 
    from your_pipeline.models import VendorRule, VCOverride
    vr = {k: VendorRule(**v) for k, v in rules["vendor_rules"].items()}
    vcr = {
        vendor: {cat: VCOverride(**ov) for cat, ov in cats.items()}
        for vendor, cats in rules["vendor_category_rules"].items()
    }
    return RuleContext(
        vendor_rules=vr,
        category_rules=rules["category_rules"],
        vendor_category_rules=vcr,
        brand_rules=rules["brand_rules"],
        default_target_margin=rules.get("default_target_margin", 0.12),
    )


def _row_to_productin(row) -> ProductIn:
    return ProductIn(
        sku=row.Product.sku,
        vendor_name=row.Vendor.name,
        brand_name=row.Brand.name if row.Brand else None,
        category_name=row.Category.name if row.Category else None,
        cost=float(row.Product.cost),
        shipping_cost=float(row.ShippingTier.shipping_cost) if row.ShippingTier else None,
    )


def _dump(out: Any) -> Dict[str, Any]:
    # Normalize pydantic/dict for pretty print
    if hasattr(out, "model_dump"):
        return out.model_dump()
    if isinstance(out, dict):
        return dict(out)
    return {
        "sku": getattr(out, "sku", None),
        "computed_price": getattr(out, "computed_price", None),
        "target_margin_used": getattr(out, "target_margin_used", None),
        "total_cost": getattr(out, "total_cost", None),
        "vendor_extra_cost_applied": getattr(out, "vendor_extra_cost_applied", None),
        "rule_source": getattr(out, "rule_source", None),
    }


def _get(out: Any, name: str) -> Any:
    return out[name] if isinstance(out, dict) else getattr(out, name)


def _eq_money(a: float, b: float) -> bool:
    return f"{a:.2f}" == f"{b:.2f}"


def _eq_margin(a: float, b: float) -> bool:
    return f"{a:.4f}" == f"{b:.4f}"


def main(limit: Optional[int] = None) -> int:
    engine = create_engine(settings.db_url, future=True)
    ctx = _rules_to_ctx(load_all_rules())

    sel = (
        select(Product, Vendor, Brand, Category, ShippingTier, RepricedProduct)
        .join(Vendor, Vendor.vendor_id == Product.vendor_id)
        .join(Brand, Brand.brand_id == Product.brand_id, isouter=True)
        .join(Category, Category.category_id == Product.category_id, isouter=True)
        .join(ShippingTier, ShippingTier.shipping_tier_id == Product.shipping_tier_id, isouter=True)
        .join(RepricedProduct, RepricedProduct.sku == Product.sku)
        .order_by(Product.sku)
    )
    if limit:
        sel = sel.limit(limit)

    mismatches: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    total = 0

    with Session(engine) as s:
        rows = s.execute(sel).all()
        for row in rows:
            total += 1

            pin = _row_to_productin(row)
            out = compute_price(pin, ctx)  # dict or pydantic

            saved = row.RepricedProduct

            ok_price = _eq_money(float(_get(out, "computed_price")), float(saved.computed_price))
            ok_tm = _eq_margin(float(_get(out, "target_margin_used")), float(saved.target_margin_used))
            ok_tc = _eq_money(float(_get(out, "total_cost")), float(saved.total_cost))
            ok_extra = _eq_money(float(_get(out, "vendor_extra_cost_applied")), float(saved.vendor_extra_cost_applied))
            ok_rule = str(_get(out, "rule_source")) == str(saved.rule_source)

            if not (ok_price and ok_tm and ok_tc and ok_extra and ok_rule):
                mismatches.append((
                    pin.sku,
                    _dump(out),
                    {
                        "computed_price": float(saved.computed_price),
                        "target_margin_used": float(saved.target_margin_used),
                        "total_cost": float(saved.total_cost),
                        "vendor_extra_cost_applied": float(saved.vendor_extra_cost_applied),
                        "rule_source": saved.rule_source,
                    },
                ))

    print(f"[verify] compared {total} products, mismatches: {len(mismatches)}")
    for sku, recomputed, stored in mismatches[:20]:
        print(f"  SKU={sku}")
        print(f"    recomputed: {recomputed}")
        print(f"    stored    : {stored}")

    if mismatches:
        print("\n[verify] FAIL: repricing differences detected.")
        return 1

    print("[verify] OK: repricing matches stored results.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    raise SystemExit(main(limit=args.limit))
