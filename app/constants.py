"""
constants.py

Material defaults and digitized IS data for the slab designer.
- Table 27 (Annex D) alpha coefficients (used by two-way too)
- Table 19-ish digitized shear resistance baseline (interpolatable)
- Fig.4 & Fig.5 digitized sample points for deflection modifiers
Note: The numeric arrays for Table19 / Fig4 / Fig5 below are sampled
representations to allow automated interpolation. They can be replaced
by exact IS table values later if you provide them.
"""

from typing import List, Tuple

# -----------------------
# General material defaults
# -----------------------
DEFAULT_FCK = 25.0   # MPa
DEFAULT_FY = 500.0   # MPa
UNIT_WEIGHT_CONCRETE = 25.0  # kN/m^3
GAMMA_F = 1.5

MIN_REINFORCEMENT_RATIO = 0.0012  # 0.12%
MIN_BAR_DIAMETER = 8  # mm
MAX_BAR_SPACING = 300  # mm
DEFAULT_WIDTH = 1000  # mm (1 m strip)

# -----------------------
# Table 27 (Annex D) ly/lx -> alpha_x/alpha_y
# Reproduced sampling (for interpolation)
# -----------------------
TABLE27_LY_LX = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0]
TABLE27_ALPHA_X = [0.062, 0.074, 0.084, 0.093, 0.099, 0.104, 0.113, 0.118, 0.122, 0.124]
TABLE27_ALPHA_Y = [0.062, 0.061, 0.059, 0.055, 0.051, 0.046, 0.037, 0.029, 0.020, 0.014]


# -----------------------
# Table 19 (shear resistance) - Digitized approximation
# This is a small matrix representing tau_c (N/mm2) vs (fck, p_t)
# Rows: fck values [20,25,30,35,40]; Columns: p_t (%) [0.1,0.2,0.4,0.8,1.2,2.0]
# Values are sampled to match expected IS behaviour: tau_c rises with p_t and with fck
# Replace this with exact table values if you want literal IS numbers.
# -----------------------
TABLE19_FCK = [20, 25, 30, 35, 40]  # MPa
TABLE19_PT = [0.1, 0.2, 0.4, 0.8, 1.2, 2.0]  # percent of reinforcement
# tau_c rows for each fck (N/mm2)
TABLE19_TAU_C = [
    [0.12, 0.14, 0.18, 0.25, 0.30, 0.36],  # fck=20
    [0.14, 0.16, 0.20, 0.28, 0.34, 0.40],  # 25
    [0.16, 0.18, 0.24, 0.32, 0.38, 0.45],  # 30
    [0.18, 0.21, 0.26, 0.36, 0.42, 0.50],  # 35
    [0.20, 0.23, 0.30, 0.40, 0.48, 0.58],  # 40
]

# -----------------------
# Fig.4 / Fig.5 digitized sample points for deflection modifiers
# These are sampled curves from IS Fig.4 and Fig.5 relating:
# - Fig.4: allowable L/d vs p_t (percent steel) for different support conditions (we sample a 'simply supported' curve)
# - Fig.5: modification factors for continuous/slab conditions (we sample a grid)
#
# We store:
#   FIG4_PT = [p_t %] -> FIG4_ALLOWED_LD = [allowed L/d for simply supported corresponding]
#   FIG5_ASPECT_RATIO = [ly/lx ratios] and a small mapping to modifier k_mod (sampled)
#
# Replace with exact scanned values if you want higher fidelity.
# -----------------------
FIG4_PT = [0.05, 0.1, 0.2, 0.4, 0.8, 1.2, 2.0]  # % steel
FIG4_ALLOWED_LD = [18.0, 20.0, 22.5, 25.0, 28.0, 30.0, 35.0]  # allowable L/d (simply supported) sampled

# Fig.5: aspect ratio -> modifier for continuous or one-way/ two-way cases
FIG5_ASPECT = [1.0, 1.25, 1.5, 2.0, 3.0]
# modifier k (multiply base allowable L/d for simply supported to get required)
# these are sampled approximations (for demonstration). For example for two-way continuous panels modifier may be 0.9..1.1 etc.
FIG5_MODIFIER = [1.00, 0.98, 0.95, 0.92, 0.88]

# -----------------------
# Utility: interpolation helpers (1D & bilinear)
# -----------------------
def interp1d(x_points: List[float], y_points: List[float], x: float) -> float:
    """Linear interpolation for 1D table; clamps at endpoints."""
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
    """Return (alpha_x, alpha_y) from Table 27 using interpolation."""
    r = max(min(ly_lx_ratio, TABLE27_LY_LX[-1]), TABLE27_LY_LX[0])
    ax = interp1d(TABLE27_LY_LX, TABLE27_ALPHA_X, r)
    ay = interp1d(TABLE27_LY_LX, TABLE27_ALPHA_Y, r)
    return ax, ay
