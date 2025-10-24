from __future__ import annotations
from typing import Dict, Any, Optional
from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE

from your_pipeline.clients.api_client import ApiClient
from your_pipeline.db.repo import Database
from your_pipeline.pricing import rules_loader
from your_pipeline.models import ProductIn, RuleContext, VendorRule, VCOverride
from your_pipeline.pricing.engine import compute_price


def _rules_to_ctx(rules_dict: Dict[str, Any]) -> RuleContext:
    vendor_rules = {k: VendorRule(**v) for k, v in rules_dict["vendor_rules"].items()}
    vc_rules: Dict[str, Dict[str, VCOverride]] = {
        ven: {cname: VCOverride(**spec) for cname, spec in cats.items()}
        for ven, cats in rules_dict["vendor_category_rules"].items()
    }
    return RuleContext(
        vendor_rules=vendor_rules,
        category_rules=rules_dict["category_rules"],
        vendor_category_rules=vc_rules,
        brand_rules=rules_dict["brand_rules"],
        default_target_margin=rules_dict.get("default_target_margin", 0.12),
    )


@task(retries=2, retry_delay_seconds=5)
def extract_all() -> Dict[str, Any]:
    api = ApiClient()
    try:
        vendors = api.get_vendors()
        per_vendor: Dict[str, Any] = {}
        for v in vendors:
            vid = v.get("vendor_id", v.get("id"))
            vid_key = str(vid)  # JSON/pickling friendly
            per_vendor[vid_key] = {
                "vendor": v,
                "brands": api.get_brands(vid),
                "categories": api.get_categories(vid),
                "shipping_tiers": api.get_shipping_tiers(vid),
                "products": api.get_products(vid),
            }
        return {"vendors": vendors, "per_vendor": per_vendor}
    finally:
        api.close()


@task(cache_policy=NO_CACHE)
def load_dim_tables(extracted: Dict[str, Any]) -> None:
    db = Database()
    vendors = [
        {"vendor_id": v.get("vendor_id", v.get("id")), "name": v["name"]}
        for v in extracted["vendors"]
    ]
    db.upsert_vendors(vendors)

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
        db.upsert_brands(brands)
        db.upsert_categories(cats)
        db.upsert_shipping_tiers(tiers)


@task(cache_policy=NO_CACHE)
def transform_and_load_products(extracted: Dict[str, Any], rules_ctx: RuleContext) -> Dict[str, int]:
    db = Database()
    repriced_rows = []
    raw_rows = []

    # helper: build id->name maps + tier->cost per vendor
    def maps(bundle):
        brand_map = {b["brand_id"]: b["name"] for b in bundle["brands"]}
        cat_map   = {c["category_id"]: c["name"] for c in bundle["categories"]}
        tier_cost = {t["shipping_tier_id"]: float(t.get("shipping_cost", 0)) for t in bundle["shipping_tiers"]}
        return brand_map, cat_map, tier_cost

    for vid_key, bundle in extracted["per_vendor"].items():
        vendor_name = bundle["vendor"]["name"]
        brand_map, cat_map, tier_cost = maps(bundle)

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

            stid = p.get("shipping_tier_id")
            shipping_cost: Optional[float] = None if stid is None else tier_cost.get(stid, 0.0)

            pi = ProductIn(
                sku=p["sku"],
                vendor_name=vendor_name,
                brand_name=brand_map.get(p.get("brand_id")),
                category_name=cat_map.get(p.get("category_id")),
                cost=float(p["cost"]),
                shipping_cost=shipping_cost,
            )

            out = compute_price(pi, rules_ctx)
            # normalize pydantic/dict for write
            if hasattr(out, "model_dump"):
                repriced_rows.append(out.model_dump())
            elif isinstance(out, dict):
                repriced_rows.append(dict(out))
            else:
                repriced_rows.append({
                    "sku": getattr(out, "sku", pi.sku),
                    "computed_price": float(getattr(out, "computed_price")),
                    "target_margin_used": float(getattr(out, "target_margin_used")),
                    "total_cost": float(getattr(out, "total_cost")),
                    "vendor_extra_cost_applied": float(getattr(out, "vendor_extra_cost_applied")),
                    "rule_source": str(getattr(out, "rule_source")),
                })

    db.upsert_products(raw_rows)
    db.upsert_repricings(repriced_rows)
    return {"products": len(raw_rows), "repriced": len(repriced_rows)}


@flow(name="repricing_flow")
def repricing_flow():
    log = get_run_logger()
    rules_ctx = _rules_to_ctx(rules_loader.load_all_rules())

    log.info("Extracting from API…")
    extracted = extract_all()

    log.info("Loading dimension tables…")
    load_dim_tables(extracted)

    log.info("Transforming and loading products…")
    counts = transform_and_load_products(extracted, rules_ctx)

    log.info(f"Done. Loaded {counts.get('products', 0)} products; repriced {counts.get('repriced', 0)}.")
