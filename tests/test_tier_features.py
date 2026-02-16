"""Tests for all three tiers of new features.

Covers:
- Tier A: Kzt passthrough, footing check, wind speed lookup, embedment override
- Tier B: Multi-segment, quantities, gate/corner posts
- Tier C: Sch80 pipes, deflection check, CSV parser readiness
"""

from __future__ import annotations

import math

import pytest

from windcalc import EstimateInput, calculate, calculate_project
from windcalc.footing import SOIL_CLASSES, compute_footing_check
from windcalc.post_catalog import (
    POST_TYPES,
    compute_deflection_check,
    moment_of_inertia_pipe,
    section_modulus_pipe,
)
from windcalc.quantities import compute_segment_quantities
from windcalc.schemas import ProjectInput, SegmentInput
from windcalc.wind_speed_lookup import lookup_wind_speed

# ── Tier A: Engineering Accuracy ──────────────────────────────────────


class TestKztPassthrough:
    """Tier A #3: Topographic factor Kzt."""

    def test_kzt_default_is_one(self):
        inp = EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10
        )
        assert inp.kzt == 1.0

    def test_kzt_increases_pressure(self):
        out1 = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10, kzt=1.0,
        ))
        out2 = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10, kzt=1.5,
        ))
        assert out2.shared.pressure_psf > out1.shared.pressure_psf

    def test_kzt_shows_in_design_params(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10, kzt=1.3,
        ))
        assert out.shared.design_params.kzt == 1.3

    def test_kzt_in_assumptions(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10, kzt=1.5,
        ))
        assumptions_text = " ".join(out.line.assumptions)
        assert "user-specified topographic factor" in assumptions_text


class TestFootingCheck:
    """Tier A #2: IBC 1807.3 footing check."""

    def test_footing_check_basic(self):
        fc = compute_footing_check(
            load_per_post_lb=500,
            height_above_grade_ft=8,
            footing_diameter_in=16,
            embedment_depth_in=36,
            soil_class="gravel",
        )
        assert fc.overturning_moment_ft_lb == 2000.0
        assert fc.footing_diameter_in == 16
        assert fc.safety_factor > 0

    def test_footing_adequate_for_deep_embedment(self):
        fc = compute_footing_check(
            load_per_post_lb=200,
            height_above_grade_ft=6,
            footing_diameter_in=12,
            embedment_depth_in=72,
            soil_class="gravel",
        )
        assert fc.footing_ok is True
        assert fc.safety_factor >= 1.5

    def test_footing_fails_for_shallow_embedment(self):
        fc = compute_footing_check(
            load_per_post_lb=1000,
            height_above_grade_ft=12,
            footing_diameter_in=10,
            embedment_depth_in=18,
            soil_class="clay",
        )
        assert fc.footing_ok is False
        assert fc.safety_factor < 1.5

    def test_soil_classes_all_have_values(self):
        for _key, (label, value) in SOIL_CLASSES.items():
            assert isinstance(label, str)
            assert value >= 0

    def test_footing_result_in_engine_output(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
        ))
        assert out.line.footing is not None
        assert out.terminal.footing is not None
        assert out.line.footing.safety_factor > 0

    def test_embedment_override(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
            embedment_depth_in=60,
        ))
        assert out.line.footing.actual_embedment_ft == 5.0


class TestWindSpeedLookup:
    """Tier A #4: ZIP code wind speed lookup."""

    def test_known_zip_florida(self):
        speed, region = lookup_wind_speed("33101", "II")
        assert speed is not None
        assert speed >= 130
        assert "Florida" in region

    def test_known_zip_midwest(self):
        speed, _region = lookup_wind_speed("60601", "II")
        assert speed is not None
        assert speed >= 90

    def test_risk_category_scaling(self):
        speed_ii, _ = lookup_wind_speed("23220", "II")
        speed_iii, _ = lookup_wind_speed("23220", "III")
        assert speed_iii > speed_ii

    def test_invalid_zip(self):
        speed, _region = lookup_wind_speed("00", "II")
        assert speed is None

    def test_unknown_zip_prefix(self):
        _speed, region = lookup_wind_speed("99999", "II")
        # May or may not be in database; should not crash
        assert isinstance(region, str)


# ── Tier B: PM Flexibility ────────────────────────────────────────────


class TestMultiSegment:
    """Tier B #5: Multi-segment analysis."""

    def test_single_segment_project(self):
        proj = ProjectInput(
            wind_speed_mph=120,
            exposure="C",
            segments=[
                SegmentInput(
                    height_total_ft=8, post_spacing_ft=10, fence_length_ft=200,
                ),
            ],
        )
        result = calculate_project(proj)
        assert len(result.segments) == 1
        assert result.overall_status in ("GREEN", "YELLOW", "RED")
        assert result.total_quantities is not None

    def test_multi_segment_aggregation(self):
        proj = ProjectInput(
            wind_speed_mph=120,
            exposure="C",
            segments=[
                SegmentInput(
                    label="North Run", height_total_ft=8,
                    post_spacing_ft=10, fence_length_ft=200,
                ),
                SegmentInput(
                    label="South Run", height_total_ft=6,
                    post_spacing_ft=8, fence_length_ft=150,
                ),
            ],
        )
        result = calculate_project(proj)
        assert len(result.segments) == 2
        assert result.segments[0].label == "North Run"
        assert result.segments[1].label == "South Run"
        total_q = result.total_quantities
        assert total_q.fence_length_ft == 350.0
        assert total_q.total_posts > 0

    def test_worst_status_propagates(self):
        proj = ProjectInput(
            wind_speed_mph=150,
            exposure="D",
            segments=[
                SegmentInput(
                    height_total_ft=6, post_spacing_ft=6, fence_length_ft=100,
                ),
                SegmentInput(
                    height_total_ft=12, post_spacing_ft=10, fence_length_ft=100,
                    line_post_key="1_7_8_PIPE",
                ),
            ],
        )
        result = calculate_project(proj)
        assert result.overall_status in ("YELLOW", "RED")


class TestQuantities:
    """Tier B #8: Material quantity takeoff."""

    def test_basic_quantities(self):
        sq = compute_segment_quantities(
            fence_length_ft=200, height_ft=8, post_spacing_ft=10,
        )
        assert sq.num_line_posts >= 18  # 200/10 = 20 bays, -1 = 19 line posts
        assert sq.num_terminal_posts == 2
        assert sq.total_posts > 0
        assert sq.top_rail_lf == 200.0
        assert sq.fabric_sf == 1600.0
        assert sq.total_concrete_cf > 0
        assert sq.total_concrete_cy > 0

    def test_quantities_in_engine_output(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
            fence_length_ft=200,
        ))
        assert out.quantities is not None
        assert out.quantities.total_posts > 0
        assert out.quantities.top_rail_lf > 0

    def test_no_quantities_without_length(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
        ))
        assert out.quantities is None

    def test_gate_and_corner_counts(self):
        sq = compute_segment_quantities(
            fence_length_ft=200, height_ft=8, post_spacing_ft=10,
            num_terminals=2, num_corners=4, num_gates=2,
        )
        assert sq.num_corner_posts == 4
        assert sq.num_gate_posts == 2
        assert sq.total_posts == sq.num_line_posts + 2 + 4 + 2


class TestGateCornerPosts:
    """Tier B #7: Gate/corner as distinct roles."""

    def test_gate_post_key_accepted(self):
        inp = EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
            gate_post_key="4_0_PIPE", num_gates=2,
        )
        assert inp.gate_post_key == "4_0_PIPE"
        assert inp.num_gates == 2

    def test_corner_post_key_accepted(self):
        inp = EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
            corner_post_key="3_1_2_SS40", num_corners=3,
        )
        assert inp.corner_post_key == "3_1_2_SS40"
        assert inp.num_corners == 3


# ── Tier C: Reliability & Polish ──────────────────────────────────────


class TestSchedule80Pipes:
    """Tier C #12: Sch80 pipe variants."""

    def test_sch80_posts_exist_in_catalog(self):
        assert "2_3_8_S80" in POST_TYPES
        assert "2_7_8_S80" in POST_TYPES
        assert "3_1_2_S80" in POST_TYPES
        assert "4_0_S80" in POST_TYPES

    def test_sch80_thicker_wall_than_ss40(self):
        assert POST_TYPES["2_3_8_S80"].wall_in > POST_TYPES["2_3_8_SS40"].wall_in
        assert POST_TYPES["2_7_8_S80"].wall_in > POST_TYPES["2_7_8_SS40"].wall_in

    def test_sch80_same_od_as_ss40(self):
        assert POST_TYPES["2_3_8_S80"].od_in == POST_TYPES["2_3_8_SS40"].od_in

    def test_sch80_higher_section_modulus(self):
        s_ss40 = section_modulus_pipe(
            POST_TYPES["2_3_8_SS40"].od_in, POST_TYPES["2_3_8_SS40"].wall_in,
        )
        s_s80 = section_modulus_pipe(
            POST_TYPES["2_3_8_S80"].od_in, POST_TYPES["2_3_8_S80"].wall_in,
        )
        assert s_s80 > s_ss40

    def test_sch80_post_usable_in_engine(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
            line_post_key="2_3_8_S80", terminal_post_key="3_1_2_S80",
        ))
        assert out.line.post_key == "2_3_8_S80"
        assert out.terminal.post_key == "3_1_2_S80"


class TestDeflectionCheck:
    """Tier C #10: Post deflection (serviceability) check."""

    def test_deflection_check_returns_values(self):
        defl, allow, ok = compute_deflection_check(
            post_key="2_3_8_SS40", height_ft=8, load_per_post_lb=300,
        )
        assert defl > 0
        assert allow > 0
        assert isinstance(ok, bool)

    def test_heavier_post_less_deflection(self):
        d1, _, _ = compute_deflection_check(
            "2_3_8_SS40", 8, 300,
        )
        d2, _, _ = compute_deflection_check(
            "4_0_PIPE", 8, 300,
        )
        assert d2 < d1

    def test_moment_of_inertia_pipe(self):
        inertia = moment_of_inertia_pipe(2.375, 0.130)
        assert inertia > 0
        expected = math.pi * (2.375**4 - (2.375 - 0.26)**4) / 64
        assert inertia == pytest.approx(expected, rel=1e-6)

    def test_deflection_in_engine_output(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
        ))
        assert out.line.deflection is not None
        assert out.line.deflection.deflection_in >= 0
        assert out.line.deflection.allowable_in > 0

    def test_deflection_ratio_computed(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120, height_total_ft=8, post_spacing_ft=10,
        ))
        if out.line.deflection.allowable_in > 0:
            expected = round(
                out.line.deflection.deflection_in / out.line.deflection.allowable_in,
                3,
            )
            assert out.line.deflection.ratio == expected


class TestCSVParserReadiness:
    """Tier C #9: CSV parser can handle formatted data."""

    def test_table_dir_exists(self):
        from windcalc.post_catalog import TABLE_DIR
        assert TABLE_DIR.exists()

    def test_empty_dir_returns_none(self):
        from windcalc.post_catalog import compute_max_spacing_from_tables
        result = compute_max_spacing_from_tables("2_3_8_SS40", 120, 8)
        assert result is None  # No CSV files yet


class TestApiEndpoints:
    """Test new API endpoints."""

    def test_v1_project_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/api/v1/project", json={
                    "wind_speed_mph": 120,
                    "exposure": "C",
                    "segments": [
                        {
                            "height_total_ft": 8,
                            "post_spacing_ft": 10,
                            "fence_length_ft": 200,
                        },
                    ],
                })
                assert resp.status_code == 200
                data = resp.json()
                assert "segments" in data
                assert "total_quantities" in data

        asyncio.run(_test())

    def test_v1_wind_speed_lookup_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/v1/wind-speed-lookup?zip_code=33101")
                assert resp.status_code == 200
                data = resp.json()
                assert data["wind_speed_mph"] is not None

        asyncio.run(_test())

    def test_v1_soil_classes_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/v1/soil-classes")
                assert resp.status_code == 200
                data = resp.json()
                assert "soil_classes" in data
                assert len(data["soil_classes"]) >= 5

        asyncio.run(_test())
