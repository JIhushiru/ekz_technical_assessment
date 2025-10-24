import pytest
from your_pipeline.pricing.rounding import apply_rounding

@pytest.mark.parametrize("raw,expected", [
    (200.00, 199.45),
    (200.49, 199.45),
    (200.50, 199.95),
    (199.00, 199.45),
    (199.51, 199.95),
    (3.49, 3.45),
])
def test_apply_rounding_examples(raw, expected):
    assert apply_rounding(raw) == expected

def test_negative_raises():
    with pytest.raises(ValueError):
        apply_rounding(-1.0)
