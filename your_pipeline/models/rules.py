from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field, model_validator

class VendorRule(BaseModel):
    extra_cost: float = Field(ge=0)
    target_margin: float = Field(ge=0, lt=1)

class VCOverride(BaseModel):
    target_margin: Optional[float] = Field(default=None, ge=0, lt=1)
    adjustment_type: Optional[Literal["waived", "delta"]] = None
    adjustment_value: Optional[float] = None

    @model_validator(mode="after")
    def _validate_combo(self):
        if self.adjustment_type == "delta" and self.adjustment_value is None:
            raise ValueError("delta requires adjustment_value")
        return self

class RuleContext(BaseModel):
    vendor_rules: Dict[str, VendorRule] = {}
    category_rules: Dict[str, float] = {}
    vendor_category_rules: Dict[str, Dict[str, VCOverride]] = {}
    brand_rules: Dict[str, float] = {}
    default_target_margin: float = Field(0.12, ge=0, lt=1)

    @model_validator(mode="after")
    def _validate_margins(self):
        for name, val in (self.category_rules or {}).items():
            f = float(val)
            if not (0.0 <= f < 1.0):
                raise ValueError(f"category margin for '{name}' must be in [0, 1)")
        for name, val in (self.brand_rules or {}).items():
            f = float(val)
            if not (0.0 <= f < 1.0):
                raise ValueError(f"brand margin for '{name}' must be in [0, 1)")
        return self
