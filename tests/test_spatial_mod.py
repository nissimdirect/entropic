"""Tests for core.spatial_mod — gravity concentration masks."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.spatial_mod import compute_gravity_mask


class TestEmptyPoints:
    def test_returns_all_ones(self):
        mask = compute_gravity_mask([], (100, 200))
        assert mask.shape == (100, 200)
        assert mask.dtype == np.float32
        assert np.all(mask == 1.0)

    def test_returns_all_ones_with_channels(self):
        mask = compute_gravity_mask([], (50, 80, 3))
        assert mask.shape == (50, 80)
        assert np.all(mask == 1.0)


class TestGaussianFalloff:
    def test_center_is_approximately_strength(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 0.8}
        mask = compute_gravity_mask([pt], (100, 100), falloff="gaussian")
        center_val = mask[50, 50]
        assert abs(center_val - 0.8) < 0.05

    def test_edges_fade(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.2, "strength": 1.0}
        mask = compute_gravity_mask([pt], (200, 200), falloff="gaussian")
        center_val = mask[100, 100]
        corner_val = mask[0, 0]
        assert center_val > corner_val
        assert corner_val < 0.1


class TestLinearFalloff:
    def test_value_at_radius_edge_is_near_zero(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 1.0, "falloff": "linear"}
        mask = compute_gravity_mask([pt], (100, 100))
        # radius = 0.3 * min(100,100) = 30 pixels
        # point at (50, 50), edge at distance 30
        # Check a pixel near the edge
        edge_y = 50 + 30  # y=80
        if edge_y < 100:
            edge_val = mask[edge_y, 50]
            assert edge_val < 0.05

    def test_center_is_strength(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 0.7, "falloff": "linear"}
        mask = compute_gravity_mask([pt], (100, 100))
        center_val = mask[50, 50]
        assert abs(center_val - 0.7) < 0.05


class TestOverlappingPoints:
    def test_combined_via_maximum_never_exceeds_one(self):
        pt1 = {"x": 0.4, "y": 0.5, "radius": 0.3, "strength": 0.9}
        pt2 = {"x": 0.6, "y": 0.5, "radius": 0.3, "strength": 0.8}
        mask = compute_gravity_mask([pt1, pt2], (100, 100), falloff="gaussian")
        assert mask.max() <= 1.0

    def test_overlap_region_takes_max(self):
        pt1 = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 0.6, "falloff": "step"}
        pt2 = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 0.9, "falloff": "step"}
        mask = compute_gravity_mask([pt1, pt2], (100, 100))
        center_val = mask[50, 50]
        # Should be max(0.6, 0.9) = 0.9
        assert abs(center_val - 0.9) < 0.01


class TestStepFalloff:
    def test_sharp_boundary(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.2, "strength": 1.0, "falloff": "step"}
        mask = compute_gravity_mask([pt], (200, 200))
        # radius = 0.2 * 200 = 40 pixels, center at (100, 100)
        # Inside: should be 1.0
        assert mask[100, 100] == 1.0
        assert mask[100, 110] == 1.0  # 10 pixels from center, inside
        # Well outside: should be 0.0
        assert mask[0, 0] == 0.0
        assert mask[100, 180] == 0.0  # 80 pixels from center, outside


class TestCosineFalloff:
    def test_smooth_curve(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.3, "strength": 1.0, "falloff": "cosine"}
        mask = compute_gravity_mask([pt], (100, 100))
        center_val = mask[50, 50]
        # At center, cos(0) = 1, so 0.5*(1+1) = 1.0
        assert abs(center_val - 1.0) < 0.05
        # Outside radius should be 0
        assert mask[0, 0] == 0.0

    def test_midpoint_value(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.5, "strength": 1.0, "falloff": "cosine"}
        mask = compute_gravity_mask([pt], (100, 100))
        # r_pixels = 0.5 * min(100,100) = 50
        # At half-radius (25px): cos(pi*0.5) = 0, so 0.5*(1+0) = 0.5
        half_r_y = 50 + 25  # 25 pixels from center = half radius
        val = mask[half_r_y, 50]
        assert 0.3 < val < 0.7  # Roughly 0.5


class TestOutOfBoundsPoint:
    def test_no_crash_positive_oob(self):
        pt = {"x": 1.5, "y": 1.2, "radius": 0.3, "strength": 1.0}
        mask = compute_gravity_mask([pt], (100, 100), falloff="gaussian")
        assert mask.shape == (100, 100)
        assert mask.dtype == np.float32

    def test_no_crash_negative_oob(self):
        pt = {"x": -0.2, "y": -0.3, "radius": 0.2, "strength": 0.5}
        mask = compute_gravity_mask([pt], (100, 100), falloff="linear")
        assert mask.shape == (100, 100)

    def test_partial_blob_visible(self):
        # Point just outside right edge — its gaussian tail should bleed in
        pt = {"x": 1.1, "y": 0.5, "radius": 0.3, "strength": 1.0}
        mask = compute_gravity_mask([pt], (100, 100), falloff="gaussian")
        # Right edge pixels should have some nonzero value
        right_edge_val = mask[50, 99]
        assert right_edge_val > 0.0


class TestZeroRadius:
    def test_no_crash(self):
        pt = {"x": 0.5, "y": 0.5, "radius": 0.0, "strength": 1.0}
        mask = compute_gravity_mask([pt], (100, 100), falloff="gaussian")
        assert mask.shape == (100, 100)
        # Zero radius contributes nothing, mask stays zero
        assert mask.max() == 0.0

    def test_zero_radius_with_other_points(self):
        pt1 = {"x": 0.5, "y": 0.5, "radius": 0.0, "strength": 1.0}
        pt2 = {"x": 0.5, "y": 0.5, "radius": 0.2, "strength": 0.5, "falloff": "step"}
        mask = compute_gravity_mask([pt1, pt2], (100, 100))
        # Second point should still contribute
        assert mask[50, 50] > 0.0


class TestFrameShapes:
    def test_rectangular_wide(self):
        mask = compute_gravity_mask(
            [{"x": 0.5, "y": 0.5, "radius": 0.2, "strength": 1.0}],
            (100, 200),
            falloff="gaussian",
        )
        assert mask.shape == (100, 200)

    def test_square(self):
        mask = compute_gravity_mask(
            [{"x": 0.5, "y": 0.5, "radius": 0.2, "strength": 1.0}],
            (50, 50),
            falloff="linear",
        )
        assert mask.shape == (50, 50)

    def test_single_pixel(self):
        mask = compute_gravity_mask(
            [{"x": 0.5, "y": 0.5, "radius": 0.5, "strength": 1.0}],
            (1, 1),
            falloff="gaussian",
        )
        assert mask.shape == (1, 1)
        assert mask[0, 0] > 0.0
