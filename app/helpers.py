"""
helpers.py

Utility functions:
- unit conversion
- spans and cover calculations
- load computations
- interpolation wrappers (using constants.interp1d)
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
# Lc = centre-to-centre span provided. Effective span usually = max( Lc, (L + support width)/2 )
# We accept input as clear span Lc (m) and support width (m)
# -----------------------
def effective_span_clear(Lc_m: float, support_width_m: float) -> float:
    return max(Lc_m, (Lc_m + support_width_m) / 2.0)

# -----------------------
# Self-weight of slab per metre width (kN/m)
# thickness_mm -> kN/m for 1m width
# -----------------------
def slab_self_weight_mm(thickness_mm: float) -> float:
    thickness_m = thickness_mm / 1000.0
    return UNIT_WEIGHT_CONCRETE * thickness_m  # kN/m per 1m width

# -----------------------
# Total dead load (kN/m) for 1m strip
# self_weight_kN_per_m, floor_finish_kN_per_m, partitions_kN_per_m are kN/m already
# -----------------------
def total_dead_load(self_weight_kN_per_m: float, floor_finish_kN_per_m: float, partitions_kN_per_m: float) -> float:
    return self_weight_kN_per_m + floor_finish_kN_per_m + partitions_kN_per_m

# -----------------------
# Factored (ultimate) uniformly distributed load (kN/m)
# w_u = 1.5 * (DL + LL) — IS simplification
# -----------------------
def factored_load(dl_kN_per_m: float, ll_kN_per_m: float) -> float:
    return GAMMA_F * (dl_kN_per_m + ll_kN_per_m)

# -----------------------
# Simple 1D interpolation wrapper (delegates to constants.interp1d)
# -----------------------
def interp1d_wrapper(x_pts, y_pts, x):
    return interp1d(x_pts, y_pts, x)
