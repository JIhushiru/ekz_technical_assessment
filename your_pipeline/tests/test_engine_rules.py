from your_pipeline.models import (
    ProductIn, RuleContext, VendorRule, VCOverride
)
from your_pipeline.pricing.engine import compute_price


def make_ctx():
    return RuleContext(
        vendor_rules={
            "Titan Labs": VendorRule(extra_cost=20, target_margin=0.20),
            "Prime Distributors": VendorRule(extra_cost=10, target_margin=0.15),
        },
        category_rules={"Electronics": 0.35, "Toys & Kids": 0.25},
        vendor_category_rules={
            "Titan Labs": {
                "Electronics": VCOverride(
                    target_margin=0.40, adjustment_type="delta", adjustment_value=-10
                )
            }
        },
        brand_rules={"StoneBridge": 0.60},
        default_target_margin=0.12
    )

def test_vendor_category_overrides():
    ctx = make_ctx()
    p = ProductIn(
        sku="A1", vendor_name="Titan Labs", brand_name=None, category_name="Electronics",
        cost=100, shipping_cost=15
    )
    out = compute_price(p, ctx)
    assert out.vendor_extra_cost_applied == 10
    assert out.target_margin_used == 0.40
    assert out.rule_source == "vendor_category"

def test_brand_rule_when_shipping_null():
    ctx = make_ctx()
    p = ProductIn(
        sku="B1", vendor_name="Prime Distributors", brand_name="StoneBridge",
        category_name="Electronics", cost=80, shipping_cost=None
    )
    out = compute_price(p, ctx)
    assert out.rule_source == "brand"
    assert out.target_margin_used == 0.60

def test_fallback_category_then_vendor_then_default():
    ctx = make_ctx()
    # Category applies (Toys & Kids)
    p1 = ProductIn(
        sku="C1",
        vendor_name="Prime Distributors",
        brand_name=None,
        category_name="Toys & Kids",
        cost=50,
        shipping_cost=5,
    )
    o1 = compute_price(p1, ctx)
    assert o1.rule_source == "category"

    # Category missing -> vendor rule
    p2 = ProductIn(
        sku="C2",
        vendor_name="Prime Distributors",
        brand_name=None,
        category_name="Furniture & Home",
        cost=50,
        shipping_cost=5,
    )
    o2 = compute_price(p2, ctx)
    assert o2.rule_source == "vendor"

    # Unknown vendor -> default 12%
    p3 = ProductIn(
        sku="C3",
        vendor_name="Unknown Vendor",
        brand_name=None,
        category_name=None,
        cost=50,
        shipping_cost=5,
    )
    o3 = compute_price(p3, ctx)
    assert o3.rule_source == "default"

