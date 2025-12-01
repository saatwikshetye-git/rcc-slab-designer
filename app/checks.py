"""
checks.py
---------
Independent checks used in both one-way and two-way slab modules:
- minimum steel check
- spacing check
- basic deflection check (L/d rule)
"""

from .constants import (
    MIN_REINFORCEMENT_RATIO,
    MAX_BAR_SPACING
)


# ---------------------------------------------------------
# MINIMUM STEEL CHECK
# ---------------------------------------------------------

def check_minimum_steel(ast_provided, b_mm, d_mm):
    """
    Checks if provided steel >= minimum steel as per IS 456.

    Minimum steel (per metre width):
        Ast_min = 0.12% of b*d for Fe500
    """
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm

    if ast_provided < ast_min:
        return False, f"Provided Ast ({ast_provided:.1f} mm²/m) < minimum required Ast ({ast_min:.1f} mm²/m)."

    return True, None


# ---------------------------------------------------------
# SPACING CHECK
# ---------------------------------------------------------

def check_spacing(spacing_mm, bar_dia_mm):
    """
    Basic spacing check:
      - spacing should NOT exceed MAX_BAR_SPACING (IS max)
      - spacing should not be extremely small (i.e. < 75 mm)
    """
    warnings = []

    if spacing_mm > MAX_BAR_SPACING:
        warnings.append(
            f"Spacing {spacing_mm} mm exceeds IS maximum allowed {MAX_BAR_SPACING} mm."
        )

    if spacing_mm < 75:
        warnings.append(
            f"Spacing {spacing_mm} mm is very tight; practical minimum recommended is ~75 mm."
        )

    if bar_dia_mm < 8:
        warnings.append("Bar diameter below 8 mm is not recommended for slabs.")

    if warnings:
        return False, warnings
    
    return True, []


# ---------------------------------------------------------
# DEFLECTION CHECK (Simplified)
# ---------------------------------------------------------

def check_deflection(d_mm, span_m):
    """
    Checks if d/L ≥ 1/20 (very simplified check).
    Real check depends on modification factors, but this keeps it light.
    """
    span_mm = span_m * 1000.0
    ratio = d_mm / span_mm  # should be >= 1/20

    if ratio < (1/20):
        return False, f"Depth may be insufficient for deflection (d/L = {ratio:.4f}). Recommended ≥ 1/20."
    
    return True, None

