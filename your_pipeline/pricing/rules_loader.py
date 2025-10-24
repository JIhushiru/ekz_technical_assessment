from pathlib import Path
from typing import Dict, Any
import yaml

RULES_DIR = Path(__file__).resolve().parents[1] / "config" / "rules"

def _norm(s: str) -> str:
    return (
        s.strip()
         .replace("’", "'")
         .replace("＆", "&")
         .casefold()
    )

def _load_yaml(name: str) -> Dict[str, Any]:
    with open(RULES_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _normalize_vendor_rules(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        _norm(k): {
            "extra_cost": float(v.get("extra_cost", 0)),
            "target_margin": float(v.get("target_margin", 0)),
        }
        for k, v in (d or {}).items()
    }

def _normalize_simple_float_map(d: Dict[str, Any]) -> Dict[str, float]:
    return {_norm(k): float(v) for k, v in (d or {}).items()}

def _normalize_vendor_category_rules(d: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for vendor, cats in (d or {}).items():
        vkey = _norm(vendor)
        out[vkey] = {}
        for cat, spec in (cats or {}).items():
            out[vkey][_norm(cat)] = {
                "target_margin": (
                    float(spec.get("target_margin"))
                    if spec.get("target_margin") is not None else None
                ),
                "adjustment_type": spec.get("adjustment_type"),
                "adjustment_value": (
                    float(spec.get("adjustment_value"))
                    if spec.get("adjustment_value") is not None else None
                ),
            }
    return out

def load_all_rules():
    vendor = _normalize_vendor_rules(_load_yaml("vendor_rules.yaml"))          # str -> {extra_cost, target_margin}
    cat    = _normalize_simple_float_map(_load_yaml("category_rules.yaml"))    # str -> float
    vc     = _normalize_vendor_category_rules(_load_yaml("vendor_category_rules.yaml"))
    brand  = _normalize_simple_float_map(_load_yaml("brand_rules.yaml"))       # str -> float
    return {
        "vendor_rules": vendor,
        "category_rules": cat,
        "vendor_category_rules": vc,
        "brand_rules": brand,
        "default_target_margin": 0.12,
    }