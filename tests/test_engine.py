"""Tests for windcalc engine."""

import warnings

from windcalc import EstimateInput, calculate
from windcalc.engine import calculate_wind_load
from windcalc.risk import classify_risk
from windcalc.schemas import FenceSpecs, WindConditions, WindLoadRequest


def test_calculate_bay_outputs():
    inp = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
    )
    result = calculate(inp)

    assert result.pressure_psf > 0
    assert result.area_per_bay_ft2 == 80
    assert result.total_load_lb > 0
    assert result.load_per_post_lb == result.total_load_lb / 2
    assert result.recommended.post_key
    assert result.recommended.post_label
    # Footing comes from catalog for the selected post
    from windcalc.post_catalog import POST_TYPES  # inline import to avoid circulars at top

    post = POST_TYPES[result.recommended.post_key]
    assert result.recommended.footing_diameter_in == post.footing_diameter_in
    assert result.recommended.embedment_in == post.footing_embedment_in
    assert result.assumptions


def test_exposure_factor_increases_pressure():
    base = EstimateInput(
        wind_speed_mph=100,
        height_total_ft=6,
        post_spacing_ft=8,
        exposure="B",
    )
    high = base.model_copy(update={"exposure": "D"})

    base_result = calculate(base)
    high_result = calculate(high)

    assert high_result.pressure_psf > base_result.pressure_psf


def test_warning_triggered_for_tall_fence():
    inp = EstimateInput(
        wind_speed_mph=140,
        height_total_ft=14,
        post_spacing_ft=10,
        exposure="C",
    )
    result = calculate(inp)

    assert any("height exceeds" in w.lower() for w in result.warnings)


def test_line_post_bending_over_one_is_advisory_not_fail():
    """
    For line posts, bending utilization > 1.0 should NOT cause the line block
    status to go RED.  (Terminal status is determined independently.)
    """
    inp = EstimateInput(
        wind_speed_mph=150,
        height_total_ft=20,
        post_spacing_ft=5,
        exposure="C",
        post_role="line",
    )
    out = calculate(inp)

    # The LINE block status must not be RED due to bending alone
    # (spacing is within limits, and bending for line posts is advisory-only)
    assert out.line.status != "RED"

    # Line bending advisory should appear via classify_risk
    _status, details = classify_risk(
        out,
        {
            "post_spacing_ft": inp.post_spacing_ft,
            "post_role": "line",
        },
    )
    assert any(
        "Advisory - Simplified cantilever bending check (conservative)" in reason
        for reason in details.get("advanced_reasons", [])
    )


def test_terminal_post_bending_over_one_sets_fail():
    """
    For terminal posts, bending utilization > 1.0 should set status to RED.
    """
    inp = EstimateInput(
        wind_speed_mph=150,
        height_total_ft=12,
        post_spacing_ft=6,
        exposure="C",
        post_key="2_3_8_SS40",
        post_role="terminal",
    )
    out = calculate(inp)

    status, details = classify_risk(
        out,
        {
            "post_spacing_ft": inp.post_spacing_ft,
            "post_role": "terminal",
            "post_key": inp.post_key,
        },
    )

    assert status == "RED"
    assert any("Terminal bending utilization" in reason for reason in details.get("reasons", []))


def test_manual_post_key_uses_catalog_footing():
    from windcalc.post_catalog import POST_TYPES

    inp = EstimateInput(
        wind_speed_mph=100,
        height_total_ft=6,
        post_spacing_ft=8,
        exposure="C",
        post_key="2_3_8_SS40",
    )
    result = calculate(inp)

    post = POST_TYPES["2_3_8_SS40"]
    assert result.recommended.post_key == "2_3_8_SS40"
    assert result.recommended.footing_diameter_in == post.footing_diameter_in
    assert result.recommended.embedment_in == post.footing_embedment_in


def test_post_key_override_wins_over_post_size():
    inp = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=8,
        exposure="C",
        post_key="2_3_8_SS40",
        post_size='3-1/2" SS40',  # legacy label; should be ignored when post_key is present
    )
    result = calculate(inp)

    assert result.recommended.post_key == "2_3_8_SS40"
    assert result.recommended.post_label.startswith("2-3/8")


def test_swapping_post_key_changes_bending_and_spacing():
    small = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=8,
        exposure="C",
        line_post_key="2_3_8_SS40",
    )
    large = small.model_copy(update={"line_post_key": "3_1_2_SS40"})

    small_out = calculate(small)
    large_out = calculate(large)

    assert small_out.line.post_key == "2_3_8_SS40"
    assert large_out.line.post_key == "3_1_2_SS40"

    # Expect different bending capacity or spacing limits when swapping post
    assert small_out.line.M_allow_ft_lb != large_out.line.M_allow_ft_lb or (
        small_out.line.max_spacing_ft is not None
        and large_out.line.max_spacing_ft is not None
        and small_out.line.max_spacing_ft != large_out.line.max_spacing_ft
    )


def test_auto_and_manual_same_post_have_same_footing():
    """
    Auto recommendation should pick a post by bending capacity.
    Manual override of the same key must produce matching footing.
    """
    auto_inp = EstimateInput(
        wind_speed_mph=80,
        height_total_ft=6,
        post_spacing_ft=6,
        exposure="C",
    )
    auto_out = calculate(auto_inp)

    # Get whatever the capacity-based auto-selector picked
    auto_post_key = auto_out.line.post_key
    assert auto_post_key is not None

    manual_inp = auto_inp.model_copy(update={"line_post_key": auto_post_key})
    manual_out = calculate(manual_inp)

    assert auto_out.line.post_key == manual_out.line.post_key
    assert (
        auto_out.line.recommended.footing_diameter_in
        == manual_out.line.recommended.footing_diameter_in
    )
    assert (
        auto_out.line.recommended.embedment_in
        == manual_out.line.recommended.embedment_in
    )


def test_bending_output_single_location():
    """
    Line bending should appear only as advisory in advanced_reasons, not in warnings.
    Terminal bending may correctly appear in reasons (it is NOT advisory).
    """
    inp = EstimateInput(
        wind_speed_mph=150,
        height_total_ft=12,
        post_spacing_ft=6,
        exposure="C",
        line_post_key="2_3_8_SS40",
        post_role="line",
    )
    out = calculate(inp)

    _status, details = classify_risk(
        out,
        {
            "post_spacing_ft": inp.post_spacing_ft,
            "post_role": inp.post_role,
        },
    )

    adv = " ".join(details.get("advanced_reasons", []))
    warnings_joined = " ".join(out.warnings)

    # Line bending is advisory-only and must appear exactly once in advanced_reasons
    assert adv.lower().count("advisory") == 1
    # Line bending advisory text should NOT appear in engine warnings
    assert "advisory" not in warnings_joined.lower()


def test_unknown_legacy_label_falls_back_to_auto_with_warning():
    """
    Unknown legacy label should not crash; should warn and fall back to auto selection.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        inp = EstimateInput(
            wind_speed_mph=100,
            height_total_ft=6,
            post_spacing_ft=8,
            exposure="C",
            post_size="Unknown Legacy Label",
        )
        result = calculate(inp)

        # Should have produced a warning about unknown label
        assert any("Unknown post label" in str(warn.message) for warn in w)
        # Should still return a recommendation (auto)
        assert result.recommended.post_key is not None


def test_auto_selects_lightest_adequate_pipe():
    """Capacity-based auto-selector should pick the lightest pipe that passes bending."""
    from windcalc.post_catalog import compute_moment_check

    # Light load: smallest pipe should suffice
    light_inp = EstimateInput(
        wind_speed_mph=80,
        height_total_ft=6,
        post_spacing_ft=6,
        exposure="C",
    )
    light_out = calculate(light_inp)
    light_key = light_out.line.post_key
    # Verify the selected pipe actually passes the bending check
    _md, _ma, ok = compute_moment_check(
        light_key,
        light_inp.height_total_ft,
        light_out.shared.load_per_post_lb,
    )
    assert ok, f"Auto-selected {light_key} should pass bending"

    # Heavier load: should pick a bigger pipe
    heavy_inp = EstimateInput(
        wind_speed_mph=150,
        height_total_ft=12,
        post_spacing_ft=10,
        exposure="D",
    )
    heavy_out = calculate(heavy_inp)
    heavy_key = heavy_out.line.post_key
    _md, _ma, ok = compute_moment_check(
        heavy_key,
        heavy_inp.height_total_ft,
        heavy_out.shared.load_per_post_lb,
    )
    assert ok, f"Auto-selected {heavy_key} should pass bending"


def test_lever_arm_is_half_height():
    """Bending demand should use H/2 lever arm (uniform loading)."""
    # Known case: 120 mph, 8 ft, Exp C, 2-3/8" SS40
    inp = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
        line_post_key="2_3_8_SS40",
    )
    out = calculate(inp)
    # M_demand in ft-lb = load_per_post * (H/2) in ft
    expected_ft_lb = out.shared.load_per_post_lb * (8.0 / 2.0)
    assert out.line.M_demand_ft_lb is not None
    assert abs(out.line.M_demand_ft_lb - expected_ft_lb) < 0.5


def test_auto_post_key_treated_as_none():
    """When post_key is 'auto', engine should auto-select (not treat it as a real key)."""
    inp_auto = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
        post_key="auto",
    )
    inp_none = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
    )
    out_auto = calculate(inp_auto)
    out_none = calculate(inp_none)

    assert out_auto.line.post_key == out_none.line.post_key
    assert out_auto.line.post_key in (
        "1_7_8_PIPE", "2_3_8_SS40", "2_7_8_SS40", "3_1_2_SS40",
        "4_0_PIPE", "6_5_8_PIPE", "8_5_8_PIPE",
    )


def test_estimate_input_area_per_bay():
    inp = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
    )
    assert inp.area_per_bay_ft2 == 80


def test_legacy_api_still_available():
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind = WindConditions(wind_speed=90.0, exposure_category="B", importance_factor=1.0)
    request = WindLoadRequest(fence=fence, wind=wind, project_name="Test")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = calculate_wind_load(request)

    assert result.design_pressure > 0
    assert result.total_load > 0
    assert result.fence_specs == fence
    assert result.wind_conditions == wind
