"""
constants.py
-----------
Constants and IS table data for the slab designer.

Includes:
- Material defaults and safety factors.
- Table 27 (IS 456:2000 Annex D) alpha coefficients for two-way slabs (simply-supported on four sides).
- An interpolation helper to get alpha_x/alpha_y for any ly/lx ratio within table range.
"""

from typing import Tuple, List

# ---------------------------------------------------------
# MATERIAL PROPERTIES / GENERAL CONSTANTS
# ---------------------------------------------------------

GAMMA_F = 1.5
GAMMA_M = 1.5

UNIT_WEIGHT_CONCRETE = 25.0   # kN/m3

MIN_REINFORCEMENT_RATIO = 0.0012  # 0.12% for Fe500 (typical)
MIN_BAR_DIAMETER = 8
MAX_BAR_SPACING = 300  # mm

DEFAULT_WIDTH = 1000  # mm (1 m strip)
DEFAULT_FCK = 25
DEFAULT_FY = 500

# ---------------------------------------------------------
# IS 456:2000 - Table 27 (Bending moment coefficients) for
# slabs spanning in two directions, simply supported on four sides.
#
# Columns correspond to l_y / l_x values:
# [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0]
#
# Values reproduced for implementation & interpolation.
# ---------------------------------------------------------

TABLE27_LY_LX = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0]

TABLE27_ALPHA_X = [
    0.062,  # 1.0
    0.074,  # 1.1
    0.084,  # 1.2
    0.093,  # 1.3
    0.099,  # 1.4
    0.104,  # 1.5
    0.113,  # 1.75
    0.118,  # 2.0
    0.122,  # 2.5
    0.124,  # 3.0
]

TABLE27_ALPHA_Y = [
    0.062,  # 1.0
    0.061,  # 1.1
    0.059,  # 1.2
    0.055,  # 1.3
    0.051,  # 1.4
    0.046,  # 1.5
    0.037,  # 1.75
    0.029,  # 2.0
    0.020,  # 2.5
    0.014,  # 3.0
]


# ---------------------------------------------------------
# Utility: interpolate alpha for any ratio in table range
# ---------------------------------------------------------
def interpolate_table(x_points: List[float], y_points: List[float], x: float) -> float:
    """
    Linear interpolation using the table points.
    If x is outside table range, clamp to min/max.
    """
    if x <= x_points[0]:
        return y_points[0]
    if x >= x_points[-1]:
        return y_points[-1]

    for i in range(len(x_points) - 1):
        x0 = x_points[i]
        x1 = x_points[i + 1]
        if x0 <= x <= x1:
            y0 = y_points[i]
            y1 = y_points[i + 1]
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    return y_points[-1]


def get_table27_alphas(ly_lx_ratio: float) -> Tuple[float, float]:
    """
    Returns (alpha_x, alpha_y) for the given ly/lx ratio using Table 27 data.
    Clamps and linearly interpolates between tabulated values.
    Note: Table 27 is for slabs simply supported on four sides (Annex D).
    """
    ratio = max(min(ly_lx_ratio, TABLE27_LY_LX[-1]), TABLE27_LY_LX[0])
    alpha_x = interpolate_table(TABLE27_LY_LX, TABLE27_ALPHA_X, ratio)
    alpha_y = interpolate_table(TABLE27_LY_LX, TABLE27_ALPHA_Y, ratio)
    return alpha_x, alpha_y
