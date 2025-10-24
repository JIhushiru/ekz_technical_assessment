from __future__ import annotations
from typing import Dict, Any, Optional
from prefect import flow, task, get_run_logger

from your_pipeline.clients.api_client import ApiClient
from your_pipeline.db.repo import Database
from your_pipeline.pricing import rules_loader
from your_pipeline.models import ProductIn, RuleContext, VendorRule, VCOverride
from your_pipeline.pricing.engine import compute_price

def _rules_to_ctx(rules_dict: Dict[str, Any]) -> RuleContext:
    vendor_rules = {k: VendorRule(**v) for k, v in rules_dict["vendor_rules"].items()}
    vc_rules: Dict[str, Dict[str, VCOverride]] = {}
    for ven, cats in rules_dict["vendor_category_rules"].items():
        vc_rules[ven] = {cname: VCOverride(**spec) for cname, spec in cats.items()}
    return RuleContext(
        vendor_rules=vendor_rules,
        category_rules=rules_dict["category_rules"],
        vendor_category_rules=vc_rules,
        brand_rules=rules_dict["brand_rules"],
        default_target_margin=rules_dict["default_target_margin"],
    )

@task
def extract_all(api: ApiClient) -> Dict[str, Any]:
    vendors = api.get_vendors()
    per_vendor = {}
    for v in vendors:
        vid = v["vendor_id"] if "vendor_id" in v else v["id"]
        per_vendor[vid] = {
            "vendor": v,
            "brands": api.get_brands(vid),
            "categories": api.get_categories(vid),
            "shipping_tiers": api.get_shipping_tiers(vid),
            "products": api.get_products(vid),
        }
    return {"vendors": vendors, "per_vendor": per_vendor}

@task
def load_dim_tables(db: Database, extracted: Dict[str, Any]):
    vendors = [
        {"vendor_id": v["vendor_id"] if "vendor_id" in v else v["id"], "name": v["name"]}
        for v in extracted["vendors"]
    ]
    db.upsert_vendors(vendors)

    for vid, bundle in extracted["per_vendor"].items():
        brands = [{"brand_id": b["brand_id"], "vendor_id": vid, "name": b["name"]} for b in bundle["brands"]]
        cats = [{"category_id": c["category_id"], "vendor_id": vid, "name": c["name"]} for c in bundle["categories"]]
        tiers = [{"shipping_tier_id": t["shipping_tier_id"], "vendor_id": vid, "name": t.get("shipping_tier"),
                  "shipping_cost": float(t.get("shipping_cost", 0))} for t in bundle["shipping_tiers"]]
        db.upsert_brands(brands)
        db.upsert_categories(cats)
        db.upsert_shipping_tiers(tiers)

@task
def transform_and_load_products(db: Database, extracted: Dict[str, Any], rules_ctx: RuleContext):
    repriced_rows = []
    raw_rows = []

    # helper: build id->name mappings + shipping_tier->cost
    def maps(bundle):
        brand_map = {b["brand_id"]: b["name"] for b in bundle["brands"]}
        cat_map = {c["category_id"]: c["name"] for c in bundle["categories"]}
        tier_cost = {t["shipping_tier_id"]: float(t.get("shipping_cost", 0)) for t in bundle["shipping_tiers"]}
        return brand_map, cat_map, tier_cost

    for vid, bundle in extracted["per_vendor"].items():
        vendor_name = bundle["vendor"]["name"]
        brand_map, cat_map, tier_cost = maps(bundle)

        for p in bundle["products"]:
            # raw load row
            raw_rows.append({
                "sku": p["sku"],
                "vendor_id": vid,
                "name": p.get("name"),
                "cost": float(p["cost"]),
                "brand_id": p.get("brand_id"),
                "category_id": p.get("category_id"),
                "shipping_tier_id": p.get("shipping_tier_id"),
            })

            # build ProductIn for pricing
            brand_name: Optional[str] = brand_map.get(p.get("brand_id"))
            category_name: Optional[str] = cat_map.get(p.get("category_id"))
            stid = p.get("shipping_tier_id")
            shipping_cost = None if stid is None else tier_cost.get(stid, 0.0)

            pi = ProductIn(
                sku=p["sku"],
                vendor_name=vendor_name,
                brand_name=brand_name,
                category_name=category_name,
                cost=float(p["cost"]),
                shipping_cost=shipping_cost,
            )
            price = compute_price(pi, rules_ctx)
            repriced_rows.append(price.model_dump())

    # write
    db.upsert_products(raw_rows)
    db.upsert_repricings(repriced_rows)

@flow(name="repricing_flow")
def repricing_flow():
    log = get_run_logger()
    api = ApiClient()
    db = Database()

    rules_dict = rules_loader.load_all_rules()
    rules_ctx = _rules_to_ctx(rules_dict)

    log.info("Extracting from API…")
    extracted = extract_all(api)

    log.info("Loading dimensions…")
    load_dim_tables(db, extracted)

    log.info("Transforming + loading products…")
    transform_and_load_products(db, extracted, rules_ctx)

    log.info("Done.")
