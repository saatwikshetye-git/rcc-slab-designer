"""
two_way.py (IS coefficient method)
----------------------------------
Two-way slab design using IS 456 coefficient method (Table 27 for
slabs simply supported on four sides). This module interpolates alpha
coefficients from Table 27 for the given aspect ratio ly/lx and computes
Mx, My and designs Ast in both directions using the same stress-block solver.
"""

import math

from .constants import (
    get_table27_alphas,
    DEFAULT_WIDTH,
    DEFAULT_FCK,
    DEFAULT_FY,
    MIN_REINFORCEMENT_RATIO,
    MAX_BAR_SPACING
)
from .units import moment_kNm_to_Nmm
from .helpers import (
    slab_self_weight,
    total_dead_load,
    factored_load
)
from .one_way import solve_ast_from_mu

# ---------------------------------------------------------
# Main two-way design function
# ---------------------------------------------------------
def design_twoway_slab(
    Lx_m,
    Ly_m,
    # Using Table 27 (simply supported on four sides)
    live_load_kN_m2=3.0,
    floor_finish_kN_m2=0.5,
    partitions_kN_per_m=0.0,
    strip_width_m=DEFAULT_WIDTH / 1000.0,
    cover_mm=20,
    bar_dia_x_mm=10,
    bar_dia_y_mm=10,
    fck=DEFAULT_FCK,
    fy=DEFAULT_FY
):
    """
    Design two-way slab using IS Table 27 interpolation (Annex D).
    Returns a dictionary with Mx/My, Ast_x/Ast_y, spacing and warnings.
    """

    # 1) load per metre strip (kN/m)
    assumed_D_mm = 150.0 + cover_mm + max(bar_dia_x_mm, bar_dia_y_mm)/2.0
    self_wt_kN_per_m = slab_self_weight(assumed_D_mm) * strip_width_m

    floor_finish_kN_per_m = floor_finish_kN_m2 * strip_width_m
    live_load_kN_per_m = live_load_kN_m2 * strip_width_m

    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, floor_finish_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, live_load_kN_per_m)

    # 2) compute aspect ratio and fetch alpha coefficients
    # Table 27 defined for ly/lx where ly >= lx. We treat Lx as short span (L_short)
    if Ly_m >= Lx_m:
        ratio = Ly_m / Lx_m
        L_short = Lx_m
        L_long = Ly_m
        short_name = "Lx"
        long_name = "Ly"
    else:
        ratio = Lx_m / Ly_m
        L_short = Ly_m
        L_long = Lx_m
        short_name = "Ly"
        long_name = "Lx"

    alpha_x, alpha_y = get_table27_alphas(ratio)

    # 3) compute moments (kN·m per metre)
    # alpha_x multiplies w * (short span)^2, alpha_y multiplies w * (long span)^2
    Mx_kN_m = alpha_x * wu_kN_per_m * (L_short ** 2)
    My_kN_m = alpha_y * wu_kN_per_m * (L_long ** 2)

    # convert to Nmm
    Mx_Nmm = moment_kNm_to_Nmm(Mx_kN_m)
    My_Nmm = moment_kNm_to_Nmm(My_kN_m)

    # 4) choose effective depths (use conservative L/d = 20)
    d_short_mm = max((L_short * 1000.0) / 20.0, 100.0)
    d_long_mm = max((L_long * 1000.0) / 20.0, 100.0)

    b_mm = 1000.0  # per metre strip

    # 5) solve for Ast in both directions (map back to x/y consistent with inputs)
    ast_short = solve_ast_from_mu(Mx_Nmm, d_short_mm, b_mm=b_mm, fck=fck, fy=fy)
    ast_long = solve_ast_from_mu(My_Nmm, d_long_mm, b_mm=b_mm, fck=fck, fy=fy)

    # 6) enforce minimum steel
    ast_short_min = MIN_REINFORCEMENT_RATIO * b_mm * d_short_mm
    ast_long_min = MIN_REINFORCEMENT_RATIO * b_mm * d_long_mm

    short_min_flag = False
    long_min_flag = False

    if ast_short < ast_short_min:
        ast_short = ast_short_min
        short_min_flag = True
    if ast_long < ast_long_min:
        ast_long = ast_long_min
        long_min_flag = True

    # 7) bar selection & spacing for provided bar diameters
    As_short = (math.pi * (bar_dia_x_mm ** 2)) / 4.0 if Ly_m >= Lx_m else (math.pi * (bar_dia_y_mm ** 2)) / 4.0
    As_long = (math.pi * (bar_dia_y_mm ** 2)) / 4.0 if Ly_m >= Lx_m else (math.pi * (bar_dia_x_mm ** 2)) / 4.0

    spacing_short_mm = (As_short * 1000.0) / ast_short if ast_short > 0 else float('inf')
    spacing_short_mm = max(50, int(math.ceil(spacing_short_mm / 5.0) * 5))
    spacing_short_mm = min(spacing_short_mm, MAX_BAR_SPACING)
    ast_short_prov = As_short * (1000.0 / spacing_short_mm) if spacing_short_mm > 0 else 0.0

    spacing_long_mm = (As_long * 1000.0) / ast_long if ast_long > 0 else float('inf')
    spacing_long_mm = max(50, int(math.ceil(spacing_long_mm / 5.0) * 5))
    spacing_long_mm = min(spacing_long_mm, MAX_BAR_SPACING)
    ast_long_prov = As_long * (1000.0 / spacing_long_mm) if spacing_long_mm > 0 else 0.0

    # 8) produce warnings & mapping back to original directions
    warnings = []
    if spacing_short_mm > MAX_BAR_SPACING:
        warnings.append(f"Short-direction spacing ({spacing_short_mm} mm) exceeds IS max {MAX_BAR_SPACING} mm.")
    if spacing_long_mm > MAX_BAR_SPACING:
        warnings.append(f"Long-direction spacing ({spacing_long_mm} mm) exceeds IS max {MAX_BAR_SPACING} mm.")
    if short_min_flag:
        warnings.append("Short-direction steel set to minimum reinforcement.")
    if long_min_flag:
        warnings.append("Long-direction steel set to minimum reinforcement.")

    # deflection heuristic
    if (d_short_mm / (L_short * 1000.0)) < (1.0 / 20.0):
        warnings.append("Short-direction: effective depth may be small for deflection (d/L < 1/20).")
    if (d_long_mm / (L_long * 1000.0)) < (1.0 / 20.0):
        warnings.append("Long-direction: effective depth may be small for deflection (d/L < 1/20).")

    # Map results to original X/Y naming (so UI shows Lx/Ly as entered)
    if Ly_m >= Lx_m:
        result = {
            "slab_type": "Two-way (IS Table 27 - simply supported 4 sides)",
            "ly_lx_ratio": round(ratio, 3),
            "wu_kN_per_m": round(wu_kN_per_m, 3),
            "alpha_short": round(alpha_x, 5),
            "alpha_long": round(alpha_y, 5),
            "L_short_m": round(L_short, 3),
            "L_long_m": round(L_long, 3),
            "Mx_kN_m_per_m": round(Mx_kN_m, 3),
            "My_kN_m_per_m": round(My_kN_m, 3),
            "d_short_mm": round(d_short_mm, 1),
            "d_long_mm": round(d_long_mm, 1),
            "Ast_short_req_mm2_per_m": round(ast_short, 2),
            "Ast_short_prov_mm2_per_m": round(ast_short_prov, 2),
            "spacing_short_mm": int(spacing_short_mm),
            "Ast_long_req_mm2_per_m": round(ast_long, 2),
            "Ast_long_prov_mm2_per_m": round(ast_long_prov, 2),
            "spacing_long_mm": int(spacing_long_mm),
            "warnings": warnings
        }
    else:
        # If Lx was longer, swap naming to match input Lx/Ly
        result = {
            "slab_type": "Two-way (IS Table 27 - simply supported 4 sides)",
            "ly_lx_ratio": round(ratio, 3),
            "wu_kN_per_m": round(wu_kN_per_m, 3),
            "alpha_short": round(alpha_x, 5),
            "alpha_long": round(alpha_y, 5),
            "L_short_m": round(L_short, 3),
            "L_long_m": round(L_long, 3),
            "Mx_kN_m_per_m": round(Mx_kN_m, 3),
            "My_kN_m_per_m": round(My_kN_m, 3),
            "d_short_mm": round(d_short_mm, 1),
            "d_long_mm": round(d_long_mm, 1),
            "Ast_short_req_mm2_per_m": round(ast_short, 2),
            "Ast_short_prov_mm2_per_m": round(ast_short_prov, 2),
            "spacing_short_mm": int(spacing_short_mm),
            "Ast_long_req_mm2_per_m": round(ast_long, 2),
            "Ast_long_prov_mm2_per_m": round(ast_long_prov, 2),
            "spacing_long_mm": int(spacing_long_mm),
            "warnings": warnings
        }

    return result
