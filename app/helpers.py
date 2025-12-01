"""
helpers.py

Utility functions:
- unit conversion
- spans and cover calculations
- load computations
- interpolation wrappers
- helper utilities (clamp, round_up)
"""

import math
from typing import Tuple

from .constants import UNIT_WEIGHT_CONCRETE, GAMMA_F, interp1d

# -----------------------
# Unit conversions
# -----------------------
def mm_to_m(mm: float) -> float:
    return mm / 1000.0

def m_to_mm(m: float) -> float:
    return m * 1000.0

def kN_to_N(kN: float) -> float:
    return kN * 1000.0

# -----------------------
# Effective span (IS 456 Clause 22.2)
# -----------------------
def effective_span_clear(Lc_m: float, support_width_m: float) -> float:
    return max(Lc_m, (Lc_m + support_width_m) / 2.0)

# -----------------------
# Self-weight of slab per metre width (kN/m)
# Maintain backward compatibility: one_way.py expects slab_self_weight()
# -----------------------
def slab_self_weight(thickness_mm: float) -> float:
    return UNIT_WEIGHT_CONCRETE * (thickness_mm / 1000.0)

# Old name kept so NOTHING breaks
def slab_self_weight_mm(thickness_mm: float) -> float:
    return slab_self_weight(thickness_mm)

# -----------------------
# Total dead load (kN/m)
# -----------------------
def total_dead_load(self_weight_kN_per_m: float, floor_finish_kN_per_m: float, partitions_kN_per_m: float) -> float:
    return self_weight_kN_per_m + floor_finish_kN_per_m + partitions_kN_per_m

# -----------------------
# Factored (ultimate) load
# -----------------------
def factored_load(dl_kN_per_m: float, ll_kN_per_m: float) -> float:
    return GAMMA_F * (dl_kN_per_m + ll_kN_per_m)

# -----------------------
# clamp helper
# -----------------------
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

# -----------------------
# round_up helper
# -----------------------
def round_up(value, nearest):
    if nearest == 0:
        return value
    return math.ceil(value / nearest) * nearest

# -----------------------
# Interpolation wrapper
# -----------------------
def interp1d_wrapper(x_pts, y_pts, x):
    return interp1d(x_pts, y_pts, x)
