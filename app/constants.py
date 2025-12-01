"""
constants.py
-----------
All fundamental constants used in IS 456 slab design.
This file contains only fixed values – no functions.
"""

# ---------------------------------------------------------
# MATERIAL PROPERTIES
# ---------------------------------------------------------

# Partial safety factors (IS 456:2000)
GAMMA_F = 1.5     # Load factor for DL + LL (Limit State)
GAMMA_M = 1.5     # Partial safety factor for steel & concrete

# Unit weight of materials (kN/m³)
UNIT_WEIGHT_CONCRETE = 25    # RCC slab self-weight
UNIT_WEIGHT_SCREED = 20      # Floor finish screed approx.

# ---------------------------------------------------------
# GEOMETRIC LIMITS (IS 456)
# ---------------------------------------------------------

MIN_REINFORCEMENT_RATIO = 0.0012      # For Fe500 (IS 456 Table)
MIN_BAR_DIAMETER = 8                   # Minimum dia for slab bars
MAX_BAR_SPACING = 300                  # Maximum spacing for slabs (mm)

# ---------------------------------------------------------
# DESIGN DEFAULTS
# ---------------------------------------------------------

DEFAULT_WIDTH = 1000     # 1m strip width for slab design
EFFECTIVE_SPAN_RULE = "L + effective_depth"  # IS 456 clause 22.2

# Default materials (common practice)
DEFAULT_FCK = 25         # M25 concrete
DEFAULT_FY = 500         # Fe500 steel

# ---------------------------------------------------------
# TWO-WAY SLAB COEFFICIENTS (αx, αy)
# ---------------------------------------------------------
# These are simplified typical values from IS 456 Annexure
# Full table is large → we use main common cases.

TWO_WAY_ALPHA = {
    "interior": {
        "alpha_x": 0.062,
        "alpha_y": 0.056,
    },
    "edge": {
        "alpha_x": 0.086,
        "alpha_y": 0.052,
    },
    "corner": {
        "alpha_x": 0.049,
        "alpha_y": 0.036,
    }
}

