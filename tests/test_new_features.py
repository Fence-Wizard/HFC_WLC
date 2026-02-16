"""Tests for new features: fence length B/s, Literal validation, YELLOW status, API v1."""

import pytest
from pydantic import ValidationError

from windcalc import EstimateInput, calculate
from windcalc.asce7 import CF_SOLID_LONG_FENCE, compute_cf_solid


class TestFenceLengthBsRatio:
    def test_fence_length_computes_aspect_ratio(self):
        inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
            fence_length_ft=200,
        )
        assert inp.aspect_ratio_bs == 200 / 8

    def test_no_fence_length_gives_none(self):
        inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
        )
        assert inp.aspect_ratio_bs is None

    def test_short_fence_lower_cf(self):
        """Short fence run (low B/s) should produce lower Cf than long run."""
        cf_short = compute_cf_solid(3.0)  # B/s = 3
        cf_long = CF_SOLID_LONG_FENCE  # B/s >= 20
        assert cf_short < cf_long

    def test_short_fence_lower_pressure(self):
        """Short fence run should produce lower design pressure."""
        long_inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
        )
        short_inp = long_inp.model_copy(update={"fence_length_ft": 20.0})

        long_out = calculate(long_inp)
        short_out = calculate(short_inp)

        assert short_out.shared.pressure_psf < long_out.shared.pressure_psf


class TestLiteralValidation:
    def test_valid_exposure_uppercase(self):
        inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
        )
        assert inp.exposure == "C"

    def test_valid_exposure_lowercase_normalized(self):
        inp = EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="b",
        )
        assert inp.exposure == "B"

    def test_invalid_exposure_raises(self):
        with pytest.raises(ValidationError):
            EstimateInput(
                wind_speed_mph=120,
                height_total_ft=8,
                post_spacing_ft=10,
                exposure="X",
            )

    def test_valid_risk_categories(self):
        for rc in ["I", "II", "III", "IV"]:
            inp = EstimateInput(
                wind_speed_mph=120,
                height_total_ft=8,
                post_spacing_ft=10,
                risk_category=rc,
            )
            assert inp.risk_category == rc

    def test_invalid_risk_category_raises(self):
        with pytest.raises(ValidationError):
            EstimateInput(
                wind_speed_mph=120,
                height_total_ft=8,
                post_spacing_ft=10,
                risk_category="V",
            )


class TestYellowStatus:
    def test_green_status_exists(self):
        out = calculate(EstimateInput(
            wind_speed_mph=80,
            height_total_ft=6,
            post_spacing_ft=6,
            exposure="C",
        ))
        assert out.overall_status in ("GREEN", "YELLOW", "RED")

    def test_block_has_spacing_ratio(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
            line_post_key="2_3_8_SS40",
        ))
        assert out.line.spacing_ratio is not None
        assert out.line.spacing_ratio > 0

    def test_block_has_moment_ratio(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
            line_post_key="2_3_8_SS40",
        ))
        assert out.line.moment_ratio is not None
        assert out.line.moment_ratio > 0

    def test_status_is_literal(self):
        out = calculate(EstimateInput(
            wind_speed_mph=120,
            height_total_ft=8,
            post_spacing_ft=10,
            exposure="C",
        ))
        assert out.line.status in ("GREEN", "YELLOW", "RED")
        assert out.terminal.status in ("GREEN", "YELLOW", "RED")
        assert out.overall_status in ("GREEN", "YELLOW", "RED")


class TestApiV1:
    def test_v1_estimate_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/api/v1/estimate", json={
                    "wind_speed_mph": 120,
                    "height_total_ft": 8,
                    "post_spacing_ft": 10,
                    "exposure": "C",
                })
                assert resp.status_code == 200
                data = resp.json()
                assert "shared" in data
                assert "line" in data
                assert "terminal" in data
                assert data["overall_status"] in ("GREEN", "YELLOW", "RED")

        asyncio.run(_test())

    def test_v1_fence_types_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/v1/fence-types")
                assert resp.status_code == 200
                data = resp.json()
                assert "fence_types" in data
                assert len(data["fence_types"]) > 0
                assert data["fence_types"][0]["solidity"] > 0

        asyncio.run(_test())

    def test_v1_post_types_endpoint(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.application import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/v1/post-types")
                assert resp.status_code == 200
                data = resp.json()
                assert "post_types" in data
                # Should only return pipe posts
                for pt in data["post_types"]:
                    assert pt["od_in"] is not None

        asyncio.run(_test())
