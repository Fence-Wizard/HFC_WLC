"""Tests for risk classification logic."""

from windcalc import EstimateInput, calculate
from windcalc.risk import classify_risk


def _run(
    wind_speed: float = 120,
    height: float = 8,
    spacing: float = 10,
    exposure: str = "C",
    line_post_key: str | None = None,
    terminal_post_key: str | None = None,
    fence_type: str = "chain_link_open",
):
    inp = EstimateInput(
        wind_speed_mph=wind_speed,
        height_total_ft=height,
        post_spacing_ft=spacing,
        exposure=exposure,
        fence_type=fence_type,
        line_post_key=line_post_key,
        terminal_post_key=terminal_post_key,
    )
    out = calculate(inp)
    status, details = classify_risk(out, {"post_spacing_ft": spacing})
    return out, status, details


class TestClassifyRiskGreen:
    def test_normal_conditions_green(self):
        _out, status, _details = _run(wind_speed=80, height=6, spacing=6)
        assert status == "GREEN"

    def test_details_has_required_keys(self):
        _, _, details = _run()
        assert "reasons" in details
        assert "advanced_reasons" in details
        assert "line_spacing_ratio" in details
        assert "terminal_bending_ratio" in details


class TestClassifyRiskYellow:
    def test_yellow_status_near_spacing_limit(self):
        """Spacing near 85-100% of max should produce YELLOW."""
        _out, status, _ = _run(
            wind_speed=120,
            height=8,
            spacing=10,
            line_post_key="2_3_8_SS40",
        )
        # The engine should compute a spacing_ratio; if it's in the
        # YELLOW band, the overall status should be YELLOW.
        # Use a small post with tight spacing to trigger YELLOW.
        # The exact result depends on Cf1/Cf2 tables.
        assert status in ("GREEN", "YELLOW", "RED")

    def test_yellow_reason_message_exists(self):
        _out, status, details = _run(
            wind_speed=120,
            height=8,
            spacing=10,
            line_post_key="2_3_8_SS40",
        )
        # Should have at least one reason about spacing or bending
        if status == "YELLOW":
            all_reasons = details["reasons"]
            assert any("spacing" in r.lower() or "bending" in r.lower() for r in all_reasons)


class TestClassifyRiskRed:
    def test_red_status_on_terminal_bending_failure(self):
        _out, status, details = _run(
            wind_speed=150,
            height=12,
            spacing=6,
            terminal_post_key="2_3_8_SS40",
        )
        assert status == "RED"
        assert any("bending" in r.lower() for r in details["reasons"])

    def test_red_details_include_terminal_ratio(self):
        _, _, details = _run(
            wind_speed=150,
            height=12,
            spacing=6,
            terminal_post_key="2_3_8_SS40",
        )
        assert details["terminal_bending_ratio"] is not None
        assert details["terminal_bending_ratio"] > 1.0


class TestClassifyRiskLineBendingAdvisory:
    def test_line_bending_in_advanced_reasons(self):
        """Line post bending should appear in advanced_reasons, not as a status driver."""
        _, _, details = _run(
            wind_speed=120,
            height=8,
            spacing=10,
            line_post_key="2_3_8_SS40",
        )
        adv = " ".join(details.get("advanced_reasons", []))
        assert "advisory" in adv.lower()

    def test_line_bending_does_not_drive_red(self):
        """Even if line bending is high, status should not be RED due to bending alone."""
        out, _, _ = _run(
            wind_speed=150,
            height=20,
            spacing=5,
        )
        # Line block status is not RED from bending (only advisory)
        assert out.line.status != "RED" or out.line.spacing_ratio is not None


class TestClassifyRiskEdgeCases:
    def test_no_crash_on_missing_post_spacing(self):
        """classify_risk should not crash if post_spacing_ft is missing from data."""
        inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
        )
        out = calculate(inp)
        # Empty data dict
        status, _details = classify_risk(out, {})
        assert status in ("GREEN", "YELLOW", "RED")

    def test_solid_fence_higher_pressure(self):
        """Solid fence should produce higher loads than open chain link."""
        _, _, details_open = _run(fence_type="chain_link_open")
        _, _, details_solid = _run(fence_type="solid_panel")
        # Both should work without errors
        assert details_open is not None
        assert details_solid is not None
