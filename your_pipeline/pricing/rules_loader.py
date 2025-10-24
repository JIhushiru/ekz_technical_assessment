from pathlib import Path
from typing import Dict, Any
import yaml

RULES_DIR = Path(__file__).resolve().parents[1] / "config" / "rules"

def _load_yaml(name: str) -> Dict[str, Any]:
    with open(RULES_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_all_rules():
    vendor = _load_yaml("vendor_rules.yaml")              # str -> {extra_cost, target_margin}
    cat = _load_yaml("category_rules.yaml")               # str -> float
    vc = _load_yaml("vendor_category_rules.yaml")         # vendor -> category -> {target_margin, adjustment_type, adjustment_value}
    brand = _load_yaml("brand_rules.yaml")                # str -> float
    return {
        "vendor_rules": vendor,
        "category_rules": cat,
        "vendor_category_rules": vc,
        "brand_rules": brand,
        "default_target_margin": 0.12,
    }
