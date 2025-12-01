"""
helpers.py
-----------
General helper functions for slab design:
- effective span calculation
- dead load calculation
- factored load calculation
- simple numerical tools
"""

from .constants import (
    UNIT_WEIGHT_CONCRETE,
    GAMMA_F,
    DEFAULT_WIDTH
)


# ---------------------------------------------------------
# EFFECTIVE SPAN (IS 456 Clause 22.2)
# ---------------------------------------------------------

def effective_span_clear(L, support_width):
    """
    L = centre-to-centre span in metres (user input)
    support_width = width of supporting beam/wall in metres
    """
    return max(L, (L + support_width) / 2)


# ---------------------------------------------------------
# LOAD CALCULATIONS
# ---------------------------------------------------------

def slab_self_weight(thickness_mm):
    """
    Calculate self weight of slab:
    thickness_mm → slab overall depth in mm
    returns kN/m (per metre width)
    """
    thickness_m = thickness_mm / 1000
    return UNIT_WEIGHT_CONCRETE * thickness_m


def total_dead_load(self_weight, floor_finish, partitions):
    """
    Sum of dead loads per metre run:
    All values must be in kN/m.
    """
    return self_weight + floor_finish + partitions


def factored_load(dead_load, live_load):
    """
    w_u = 1.5 * (DL + LL)
    """
    return GAMMA_F * (dead_load + live_load)


# ---------------------------------------------------------
# SIMPLE NUMERICAL UTILITIES
# ---------------------------------------------------------

def clamp(value, min_val, max_val):
    """Keep value within a limit."""
    return max(min_val, min(value, max_val))


def round_up(value, step):
    """
    Round 'value' to nearest upper step.
    Example: round_up(422, 10) → 430
    """
    if value % step == 0:
        return value
    return value + (step - value % step)

