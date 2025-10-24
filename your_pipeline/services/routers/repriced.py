from typing import List, Optional
from fastapi import APIRouter, Query, Request, Depends
from sqlalchemy import select

from your_pipeline.db.models import RepricedProduct, Product
from your_pipeline.services.models.repriced import RepricedOut

router = APIRouter(prefix="/repriced", tags=["repriced"])

def get_db(request: Request):
    return request.app.state.db

@router.get("", response_model=List[RepricedOut])
def list_repriced(
    vendor_id: Optional[int] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    brand_id: Optional[int] = Query(default=None),
    db = Depends(get_db),
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

    return [
        RepricedOut(
            sku=rp.sku,
            computed_price=float(rp.computed_price),
            rule_source=rp.rule_source,
            target_margin_used=float(rp.target_margin_used),
            total_cost=float(rp.total_cost),
            vendor_extra_cost_applied=float(rp.vendor_extra_cost_applied),
            vendor_id=prod.vendor_id,
            brand_id=prod.brand_id,
            category_id=prod.category_id,
            name=prod.name,
        )
        for rp, prod in rows
    ]
