"""Tests for ASCE 7-22 wind load calculations.

Each test includes a hand-calculated verification so the values
can be checked against a textbook or spreadsheet.
"""


import pytest

from windcalc.asce7 import (
    CF_SOLID_LONG_FENCE,
    FENCE_TYPES,
    G_RIGID,
    KD_FENCE,
    compute_cf,
    compute_cf_solid,
    compute_design_pressure,
    compute_kz,
    compute_qz,
)

# ── Kz Verification ─────────────────────────────────────────────────


class TestComputeKz:
    """Verify Kz against ASCE 7-22 Table 26.10-1 values."""

    def test_exposure_b_at_15ft(self):
        # Kz = 2.01 * (15/1200)^(2/7) = 0.575 ~ 0.57
        kz = compute_kz(15.0, "B")
        assert round(kz, 2) == 0.57

    def test_exposure_c_at_15ft(self):
        # Kz = 2.01 * (15/900)^(2/9.5) = 0.849 ~ 0.85
        kz = compute_kz(15.0, "C")
        assert round(kz, 2) == 0.85

    def test_exposure_d_at_15ft(self):
        # Kz = 2.01 * (15/700)^(2/11.5) = 1.030 ~ 1.03
        kz = compute_kz(15.0, "D")
        assert round(kz, 2) == 1.03

    def test_below_15ft_uses_15ft(self):
        """Heights below 15 ft should use z = 15 ft (ASCE 7 minimum)."""
        kz_8ft = compute_kz(8.0, "C")
        kz_15ft = compute_kz(15.0, "C")
        assert kz_8ft == kz_15ft

    def test_exposure_c_at_20ft(self):
        # Kz = 2.01 * (20/900)^(2/9.5) = 0.90
        kz = compute_kz(20.0, "C")
        assert round(kz, 2) == 0.90

    def test_exposure_c_at_25ft(self):
        # Kz = 2.01 * (25/900)^(2/9.5)
        kz = compute_kz(25.0, "C")
        expected = 2.01 * (25.0 / 900.0) ** (2.0 / 9.5)
        assert abs(kz - expected) < 1e-6

    def test_kz_increases_with_height(self):
        kz_15 = compute_kz(15.0, "C")
        kz_30 = compute_kz(30.0, "C")
        kz_50 = compute_kz(50.0, "C")
        assert kz_15 < kz_30 < kz_50

    def test_kz_increases_with_exposure(self):
        """For same height, D > C > B."""
        kz_b = compute_kz(15.0, "B")
        kz_c = compute_kz(15.0, "C")
        kz_d = compute_kz(15.0, "D")
        assert kz_b < kz_c < kz_d

    def test_invalid_exposure_raises(self):
        with pytest.raises(KeyError):
            compute_kz(15.0, "X")


# ── qz Verification ─────────────────────────────────────────────────


class TestComputeQz:
    """Verify velocity pressure against hand calculations."""

    def test_120mph_exp_c_8ft(self):
        """
        Hand calc for 120 mph, Exposure C, 8 ft fence:
          Kz = 0.8490 (z=15 ft minimum)
          qz = 0.00256 * 0.8490 * 1.0 * 0.85 * 120^2
             = 0.00256 * 0.8490 * 0.85 * 14400
             = 26.61 psf
        """
        qz = compute_qz(120.0, 8.0, "C")
        assert abs(qz - 26.61) < 0.5  # within 0.5 psf

    def test_150mph_exp_d_12ft(self):
        """
        Hand calc for 150 mph, Exposure D, 12 ft fence:
          Kz = 1.0305 (z=15 ft minimum)
          qz = 0.00256 * 1.0305 * 1.0 * 0.85 * 150^2
             = 0.00256 * 1.0305 * 0.85 * 22500
             = 50.42 psf
        """
        qz = compute_qz(150.0, 12.0, "D")
        assert abs(qz - 50.42) < 0.5

    def test_kzt_multiplier(self):
        """Topographic factor should scale qz linearly."""
        qz_flat = compute_qz(120.0, 8.0, "C", kzt=1.0)
        qz_hill = compute_qz(120.0, 8.0, "C", kzt=1.5)
        assert abs(qz_hill / qz_flat - 1.5) < 0.01

    def test_qz_proportional_to_v_squared(self):
        qz_100 = compute_qz(100.0, 8.0, "C")
        qz_200 = compute_qz(200.0, 8.0, "C")
        assert abs(qz_200 / qz_100 - 4.0) < 0.01


# ── Cf Verification ──────────────────────────────────────────────────


class TestComputeCf:
    def test_cf_solid_default_long_fence(self):
        """Default (no B/s) should return CF_SOLID_LONG_FENCE = 1.5."""
        assert compute_cf_solid() == CF_SOLID_LONG_FENCE

    def test_cf_solid_low_bs(self):
        """B/s <= 2 should give Cf = 1.2."""
        assert compute_cf_solid(1.0) == 1.2
        assert compute_cf_solid(2.0) == 1.2

    def test_cf_solid_interpolation(self):
        """B/s = 7.5 should interpolate between 1.3 (5) and 1.4 (10)."""
        cf = compute_cf_solid(7.5)
        assert abs(cf - 1.35) < 0.01

    def test_cf_solid_high_bs(self):
        """B/s >= 45 should give max Cf = 1.75."""
        assert compute_cf_solid(45.0) == 1.75
        assert compute_cf_solid(100.0) == 1.75

    def test_cf_with_solidity(self):
        """Cf = Cf_solid * solidity."""
        cf = compute_cf(0.35)  # open chain link
        expected = CF_SOLID_LONG_FENCE * 0.35
        assert abs(cf - expected) < 0.001

    def test_cf_solid_fence(self):
        """Solidity 1.0 should equal Cf_solid."""
        assert compute_cf(1.0) == CF_SOLID_LONG_FENCE

    def test_cf_zero_solidity(self):
        """Solidity 0 should give Cf = 0."""
        assert compute_cf(0.0) == 0.0


# ── Full Design Pressure ─────────────────────────────────────────────


class TestDesignPressure:
    def test_solid_fence_120mph_exp_c(self):
        """
        Full hand calc for solid fence, 120 mph, Exp C, 8 ft:
          Kz = 0.849, Kzt = 1.0, Kd = 0.85
          qz = 0.00256 * 0.849 * 1.0 * 0.85 * 14400 = 26.61 psf
          G = 0.85, Cf = 1.5 * 1.0 = 1.5
          p = 26.61 * 0.85 * 1.5 = 33.93 psf
        """
        dp = compute_design_pressure(
            wind_speed_mph=120.0,
            height_ft=8.0,
            exposure="C",
            solidity=1.0,
            fence_type="solid_panel",
        )
        assert abs(dp.design_pressure_psf - 33.93) < 1.0
        assert dp.kd == KD_FENCE
        assert dp.g == G_RIGID
        assert dp.cf_solid == CF_SOLID_LONG_FENCE
        assert dp.solidity == 1.0

    def test_open_chain_link_120mph_exp_c(self):
        """
        Open chain link (solidity=0.35), 120 mph, Exp C, 8 ft:
          qz = 26.61 psf (same as above)
          Cf = 1.5 * 0.35 = 0.525
          p = 26.61 * 0.85 * 0.525 = 11.88 psf
        """
        dp = compute_design_pressure(
            wind_speed_mph=120.0,
            height_ft=8.0,
            exposure="C",
            solidity=0.35,
            fence_type="chain_link_open",
        )
        assert abs(dp.design_pressure_psf - 11.88) < 0.5
        assert dp.solidity == 0.35

    def test_exposure_b_reduces_pressure(self):
        dp_b = compute_design_pressure(120.0, 8.0, "B", 1.0)
        dp_c = compute_design_pressure(120.0, 8.0, "C", 1.0)
        assert dp_b.design_pressure_psf < dp_c.design_pressure_psf

    def test_exposure_d_increases_pressure(self):
        dp_c = compute_design_pressure(120.0, 8.0, "C", 1.0)
        dp_d = compute_design_pressure(120.0, 8.0, "D", 1.0)
        assert dp_d.design_pressure_psf > dp_c.design_pressure_psf


# ── Fence Types ──────────────────────────────────────────────────────


class TestFenceTypes:
    def test_all_fence_types_have_valid_solidity(self):
        for key, ft in FENCE_TYPES.items():
            assert 0.0 < ft.solidity <= 1.0, f"{key} has invalid solidity"

    def test_chain_link_open_solidity(self):
        assert FENCE_TYPES["chain_link_open"].solidity == 0.35

    def test_solid_panel_solidity(self):
        assert FENCE_TYPES["solid_panel"].solidity == 1.0
