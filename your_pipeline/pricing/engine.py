from typing import Optional, Tuple
from your_pipeline.pricing.rounding import apply_rounding
from your_pipeline.models import (
    ProductIn, RuleContext, PriceResult, VCOverride
)

def _resolve_extra_cost(vendor: str, category: Optional[str], ctx: RuleContext) -> float:
    base = float(ctx.vendor_rules.get(vendor).extra_cost) if vendor in ctx.vendor_rules else 0.0
    if vendor and category:
        vc: Optional[VCOverride] = ctx.vendor_category_rules.get(vendor, {}).get(category)
        if vc:
            if vc.adjustment_type == "waived":
                return 0.0
            if vc.adjustment_type == "delta" and vc.adjustment_value is not None:
                return max(0.0, base + float(vc.adjustment_value))
    return max(0.0, base)

def _resolve_target_margin(p: ProductIn, ctx: RuleContext) -> Tuple[float, str]:
    # 1) Brand (only when shipping is null)
    if p.shipping_cost is None and p.brand_name:
        tm = ctx.brand_rules.get(p.brand_name)
        if tm is not None:
            return float(tm), "brand"

    # 2) Vendor-Category
    if p.vendor_name and p.category_name:
        vc = ctx.vendor_category_rules.get(p.vendor_name, {}).get(p.category_name)
        if vc and vc.target_margin is not None:
            return float(vc.target_margin), "vendor_category"

    # 3) Default Category
    if p.category_name and p.category_name in ctx.category_rules:
        return float(ctx.category_rules[p.category_name]), "category"

    # 4) Vendor
    vr = ctx.vendor_rules.get(p.vendor_name)
    if vr:
        return float(vr.target_margin), "vendor"

    # 5) Default
    return float(ctx.default_target_margin), "default"

def compute_price(p: ProductIn, ctx: RuleContext) -> PriceResult:
    shipping = 0.0 if p.shipping_cost is None else float(p.shipping_cost)
    extra = _resolve_extra_cost(p.vendor_name, p.category_name, ctx)
    target_margin, source = _resolve_target_margin(p, ctx)

    if not (0.0 <= target_margin < 1.0):
        raise ValueError("target_margin must be in [0,1)")

    total_cost = float(p.cost) + shipping + extra
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
