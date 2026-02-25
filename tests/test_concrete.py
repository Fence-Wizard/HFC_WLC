from windcalc.concrete import BAG_60LB_YIELD_CF, calculate_concrete_estimate
from windcalc.schemas import ConcreteEstimateInput, ConcreteHoleSpecInput


def test_concrete_single_row_without_waste():
    inp = ConcreteEstimateInput(
        hole_specs=[
            ConcreteHoleSpecInput(
                post_type="Line Post",
                hole_diameter_in=12,
                hole_depth_in=36,
                hole_count=10,
            )
        ],
        include_waste=False,
    )
    out = calculate_concrete_estimate(inp)
    assert out.total_holes == 10
    assert out.total_volume_cf > 0
    assert out.total_volume_cy > 0
    assert out.waste_percent == 0
    assert out.bags_60lb == int((out.total_volume_cf / BAG_60LB_YIELD_CF) + 0.999999)


def test_concrete_multiple_rows_with_waste():
    inp = ConcreteEstimateInput(
        hole_specs=[
            ConcreteHoleSpecInput(
                post_type="Line Post",
                hole_diameter_in=10,
                hole_depth_in=30,
                hole_count=20,
            ),
            ConcreteHoleSpecInput(
                post_type="Terminal",
                hole_diameter_in=12,
                hole_depth_in=36,
                hole_count=6,
            ),
        ],
        include_waste=True,
        waste_percent=10,
    )
    out = calculate_concrete_estimate(inp)
    assert len(out.rows) == 2
    assert out.total_holes == 26
    assert out.waste_volume_cf > 0
    assert out.total_volume_cf > out.subtotal_volume_cf
    assert out.bags_60lb > 0

