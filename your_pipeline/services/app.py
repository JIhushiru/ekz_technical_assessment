from fastapi import FastAPI, Query
from typing import Optional, List
from sqlalchemy import select
from your_pipeline.db.repo import Database
from your_pipeline.db.models import RepricedProduct, Product

app = FastAPI(title="Repriced Products API")
db = Database()

@app.get("/repriced", response_model=List[dict])
def list_repriced(
    vendor_id: Optional[int] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    brand_id: Optional[int] = Query(default=None),
):
    with db.session() as s:
        q = select(RepricedProduct, Product).join(Product, Product.sku == RepricedProduct.sku)
        if vendor_id is not None:
            q = q.where(Product.vendor_id == vendor_id)
        if category_id is not None:
            q = q.where(Product.category_id == category_id)
        if brand_id is not None:
            q = q.where(Product.brand_id == brand_id)
        rows = s.execute(q).all()

    out = []
    for rp, prod in rows:
        out.append({
            "sku": rp.sku,
            "computed_price": rp.computed_price,
            "rule_source": rp.rule_source,
            "target_margin_used": rp.target_margin_used,
            "total_cost": rp.total_cost,
            "vendor_extra_cost_applied": rp.vendor_extra_cost_applied,
            "vendor_id": prod.vendor_id,
            "brand_id": prod.brand_id,
            "category_id": prod.category_id,
            "name": prod.name,
        })
    return out
