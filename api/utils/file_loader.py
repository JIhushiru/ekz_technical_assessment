import json
from typing import Any, List, Dict
from collections import defaultdict


def load_data(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"Error: File not found at path '{path}'.")
    except json.JSONDecodeError:
        print(f"Error: File at '{path}' is not valid JSON.")
    return []


def load_grouped_data(path: str, key: str = "vendor_id") -> dict[int, list[dict]]:
    data = load_data(path)
    grouped = defaultdict(list)
    for item in data:
        grouped[item.get(key)].append(item)
    return grouped
