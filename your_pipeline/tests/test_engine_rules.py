import math
import pytest
from pydantic import ValidationError

from your_pipeline.models import ProductIn, RuleContext, VendorRule, VCOverride
from your_pipeline.pricing.engine import compute_price
from your_pipeline.pricing.rounding import apply_rounding


def norm(s: str) -> str:
    return s.strip().replace("’", "'").replace("＆", "&").casefold()


def ctx_full():
    return RuleContext(
        vendor_rules={
            norm("Evergreen Merchants"): VendorRule(extra_cost=15, target_margin=0.16),
            norm("Titan Labs"): VendorRule(extra_cost=20, target_margin=0.20),
            norm("Prime Distributors"): VendorRule(extra_cost=10, target_margin=0.15),
            norm("Pacific Supply Group"): VendorRule(extra_cost=0, target_margin=0.16),
            norm("Brightside Trading"): VendorRule(extra_cost=10, target_margin=0.15),
        },
        category_rules={
            norm("Automotive & Industrial"): 0.30,
            norm("Electronics"): 0.35,
            norm("Toys & Kids"): 0.25,
            norm("Beauty & Health"): 0.20,
            norm("Furniture & Home"): 0.25,
        },
        vendor_category_rules={
            norm("Evergreen Merchants"): {
                norm("Automotive & Industrial"): VCOverride(
                    target_margin=0.35, adjustment_type="waived", adjustment_value=None
                )
            },
            norm("Titan Labs"): {
                norm("Electronics"): VCOverride(
                    target_margin=0.40, adjustment_type="delta", adjustment_value=-10
                )
            },
            norm("Prime Distributors"): {
                norm("Toys & Kids"): VCOverride(
                    target_margin=0.30, adjustment_type="delta", adjustment_value=+10
                )
            },
            # model supports "waived" and "delta"; base extra=0 makes delta=+20 act like replace
            norm("Pacific Supply Group"): {
                norm("Furniture & Home"): VCOverride(
                    target_margin=0.35, adjustment_type="delta", adjustment_value=20
                )
            },
        },
        brand_rules={
            norm("StoneBridge"): 0.60,
            norm("BrightLeaf"): 0.60,
            norm("Night Owl"): 0.50,
            norm("SilverFox"): 0.45,
            norm("Blue Horizon"): 0.40,
            norm("StormForge"): 0.35,
            norm("RapidStream"): 0.50,
        },
        default_target_margin=0.12,
    )


def test_vc_delta_override():
    ctx = ctx_full()
    p = ProductIn(
        sku="T1",
        vendor_name="Titan Labs",
        brand_name=None,
        category_name="Electronics",
        cost=100,
        shipping_cost=15,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "vendor_category"
    assert out.target_margin_used == 0.40
    assert out.vendor_extra_cost_applied == 10.0


def test_vc_waived_extra():
    ctx = ctx_full()
    p = ProductIn(
        sku="E1",
        vendor_name="Evergreen Merchants",
        brand_name=None,
        category_name="Automotive & Industrial",
        cost=80,
        shipping_cost=10,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "vendor_category"
    assert out.target_margin_used == 0.35
    assert out.vendor_extra_cost_applied == 0.0


def test_vc_delta_from_zero_equiv_replace():
    ctx = ctx_full()
    p = ProductIn(
        sku="P1",
        vendor_name="Pacific Supply Group",
        brand_name=None,
        category_name="Furniture & Home",
        cost=50,
        shipping_cost=5,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "vendor_category"
    assert out.target_margin_used == 0.35
    assert out.vendor_extra_cost_applied == 20.0


def test_brand_overrides_margin_on_null_shipping():
    ctx = ctx_full()
    p = ProductIn(
        sku="B1",
        vendor_name="Titan Labs",
        brand_name="StoneBridge",
        category_name="Electronics",
        cost=100,
        shipping_cost=None,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "brand"
    assert out.target_margin_used == 0.60
    assert out.vendor_extra_cost_applied == 10.0
    assert math.isclose(out.total_cost, 110.0, rel_tol=1e-9)


def test_fallbacks_category_vendor_default():
    ctx = ctx_full()

    p1 = ProductIn(
        sku="C1",
        vendor_name="Brightside Trading",
        brand_name=None,
        category_name="Electronics",
        cost=50,
        shipping_cost=5,
    )
    assert compute_price(p1, ctx).rule_source == "category"

    p2 = ProductIn(
        sku="C2",
        vendor_name="Prime Distributors",
        brand_name=None,
        category_name="Not Listed",
        cost=50,
        shipping_cost=5,
    )
    assert compute_price(p2, ctx).rule_source == "vendor"

    p3 = ProductIn(
        sku="C3",
        vendor_name="Unknown Vendor",
        brand_name=None,
        category_name=None,
        cost=50,
        shipping_cost=5,
    )
    assert compute_price(p3, ctx).rule_source == "default"


def test_rounding_rules():
    assert apply_rounding(200.00) == 199.45
    assert apply_rounding(199.50) == 199.95
    assert apply_rounding(123.49) == 123.45
    assert apply_rounding(124.51) == 123.95


def test_negative_delta_not_below_zero():
    ctx = ctx_full()
    ctx.vendor_category_rules[norm("Prime Distributors")][norm("Toys & Kids")] = VCOverride(
        target_margin=0.30, adjustment_type="delta", adjustment_value=-50
    )
    p = ProductIn(
        sku="N1",
        vendor_name="Prime Distributors",
        brand_name=None,
        category_name="Toys & Kids",
        cost=40,
        shipping_cost=5,
    )
    out = compute_price(p, ctx)
    assert out.vendor_extra_cost_applied == 0.0


def test_invalid_margin_raises():
    with pytest.raises(ValidationError):
        _ = VendorRule(extra_cost=10, target_margin=1.0)


def test_default_margin_and_extra_cost_for_unknown_vendor():
    ctx = ctx_full()
    p = ProductIn(
        sku="D1",
        vendor_name="Unknown Vendor",
        brand_name=None,
        category_name=None,
        cost=100,
        shipping_cost=10,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "default"
    assert out.target_margin_used == 0.12
    assert out.vendor_extra_cost_applied == 0.0


def test_category_uses_vendor_extra_cost_numeric():
    ctx = ctx_full()
    p = ProductIn(
        sku="K1",
        vendor_name="Brightside Trading",
        brand_name=None,
        category_name="Electronics",
        cost=100,
        shipping_cost=0,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "category"
    assert out.target_margin_used == 0.35
    assert out.vendor_extra_cost_applied == 10.0


def test_vendor_rule_numeric_margin_and_extra():
    ctx = ctx_full()
    p = ProductIn(
        sku="V1",
        vendor_name="Prime Distributors",
        brand_name=None,
        category_name="Not Listed",
        cost=100,
        shipping_cost=0,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "vendor"
    assert out.target_margin_used == 0.15
    assert out.vendor_extra_cost_applied == 10.0


def test_titan_labs_toys_and_kids_example():
    ctx = ctx_full()
    p = ProductIn(
        sku="TL-TK",
        vendor_name="Titan Labs",
        brand_name=None,
        category_name="Toys & Kids",
        cost=100,
        shipping_cost=5,
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "category"
    assert out.target_margin_used == 0.25
    assert out.vendor_extra_cost_applied == 20.0
