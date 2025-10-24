from typing import Any, Optional, Tuple
from your_pipeline.models import ProductIn as ProductLike, PriceResult, RuleContext, VendorRule, VCOverride
from your_pipeline.pricing.rounding import apply_rounding

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return (
        s.strip()
         .replace("’", "'")
         .replace("＆", "&")
         .casefold()
    )

def _as_vendor_rule(vr: Any) -> Optional[dict]:
    """Return {'extra_cost': float, 'target_margin': float} or None."""
    if vr is None:
        return None
    if isinstance(vr, dict):
        return {
            "extra_cost": float(vr.get("extra_cost", 0.0)),
            "target_margin": float(vr.get("target_margin", 0.0)),
        }
    if isinstance(vr, VendorRule):
        return {
            "extra_cost": float(vr.extra_cost),
            "target_margin": float(vr.target_margin),
        }
    # unsupported type
    return None

def _as_vc_override(vc: Any) -> Optional[dict]:
    """Return {'target_margin': Optional[float], 'adjustment_type': str|None, 'adjustment_value': Optional[float]} or None."""
    if vc is None:
        return None
    if isinstance(vc, dict):
        tm = vc.get("target_margin")
        return {
            "target_margin": (float(tm) if tm is not None else None),
            "adjustment_type": vc.get("adjustment_type"),
            "adjustment_value": (float(vc.get("adjustment_value")) if vc.get("adjustment_value") is not None else None),
        }
    if isinstance(vc, VCOverride):
        return {
            "target_margin": (float(vc.target_margin) if vc.target_margin is not None else None),
            "adjustment_type": vc.adjustment_type,
            "adjustment_value": (float(vc.adjustment_value) if vc.adjustment_value is not None else None),
        }
    return None

def _resolve_extra_cost(vendor: str, category: Optional[str], ctx: RuleContext) -> float:
    v = _norm(vendor)
    c = _norm(category) if category else None

    vendor_rule = _as_vendor_rule(ctx.vendor_rules.get(v))
    base = vendor_rule["extra_cost"] if vendor_rule else 0.0

    if v and c:
        vc_raw = ctx.vendor_category_rules.get(v, {}).get(c)
        vc = _as_vc_override(vc_raw)
        if vc:
            adj_type = vc.get("adjustment_type")
            adj_val = vc.get("adjustment_value")
            if adj_type == "waived":
                return 0.0
            if adj_type == "delta" and isinstance(adj_val, (int, float)):
                return max(0.0, base + float(adj_val))
    return max(0.0, float(base))

def _resolve_target_margin(p: ProductLike, ctx: RuleContext) -> Tuple[float, str]:
    v = _norm(p.vendor_name)
    c = _norm(p.category_name) if p.category_name else None
    b = _norm(p.brand_name) if p.brand_name else None

    # Brand rule if shipping is null
    if p.shipping_cost is None and b:
        tm = ctx.brand_rules.get(b)
        if tm is not None:
            return float(tm), "brand"

    # Vendor-category rule
    if v and c:
        vc_raw = ctx.vendor_category_rules.get(v, {}).get(c)
        vc = _as_vc_override(vc_raw)
        if vc and (vc.get("target_margin") is not None):
            return float(vc["target_margin"]), "vendor_category"

    # Default category
    if c and c in ctx.category_rules:
        return float(ctx.category_rules[c]), "category"

    # Vendor rule
    vendor_rule = _as_vendor_rule(ctx.vendor_rules.get(v))
    if vendor_rule and ("target_margin" in vendor_rule):
        return float(vendor_rule["target_margin"]), "vendor"

    # Default
    return float(ctx.default_target_margin), "default"

def compute_price(p: ProductLike, ctx: RuleContext) -> Any:
    shipping = 0.0 if p.shipping_cost is None else float(p.shipping_cost)
    extra = _resolve_extra_cost(p.vendor_name, p.category_name, ctx)
    target_margin, source = _resolve_target_margin(p, ctx)

    total_cost = float(p.cost) + shipping + extra
    if not (0.0 <= target_margin < 1.0):
        raise ValueError("target_margin must be in [0,1)")
    denom = 1.0 - target_margin
    if denom <= 0.0:
        raise ValueError("Invalid margin resulting in zero/negative denominator")

    raw_price = total_cost / denom
    final_price = apply_rounding(raw_price)

    return PriceResult(
        sku=p.sku,
        computed_price=final_price,
        target_margin_used=target_margin,
        total_cost=round(total_cost, 2),
        vendor_extra_cost_applied=round(extra, 2),
        rule_source=source,
    )