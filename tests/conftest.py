"""
Conftest: reset all effect global state between test modules.

Pixel physics, temporal, destruction, sidechain, and DSP filter effects
use module-level dicts for frame-to-frame state. Without cleanup, test
files that run earlier pollute state for later test files.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_effect_state():
    """Clear all effect state dicts before each test."""
    from effects import physics, temporal, destruction, sidechain, dsp_filters

    physics._physics_state.clear()
    physics._physics_access_order.clear()
    temporal._temporal_state.clear()
    destruction._destruction_state.clear()
    sidechain._sidechain_state.clear()
    dsp_filters._phaser_state.clear()
    dsp_filters._feedback_phaser_state.clear()
    dsp_filters._spectral_freeze_state.clear()
    dsp_filters._reverb_state.clear()
    dsp_filters._freq_flanger_state.clear()

    yield

    # Also clear after test to prevent leaks in other direction
    physics._physics_state.clear()
    physics._physics_access_order.clear()
    temporal._temporal_state.clear()
    destruction._destruction_state.clear()
    sidechain._sidechain_state.clear()
    dsp_filters._phaser_state.clear()
    dsp_filters._feedback_phaser_state.clear()
    dsp_filters._spectral_freeze_state.clear()
    dsp_filters._reverb_state.clear()
    dsp_filters._freq_flanger_state.clear()
