import math

def apply_rounding(price_raw: float) -> float:
    """
    Rounding rule:
      1) Lower the whole number to the nearest LOWER odd number (floor then if even -> minus 1).
      2) If fractional part >= .50 => set decimal to .95
         else => set decimal to .45
    """
    if price_raw < 0:
        raise ValueError("Price cannot be negative")

    whole = math.floor(price_raw)
    if whole % 2 == 0:
        whole -= 1
    frac = price_raw - math.floor(price_raw)
    cents = 0.95 if frac >= 0.50 else 0.45
    return round(whole + cents, 2)
