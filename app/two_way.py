"""
two_way.py
----------
Two-way slab design engine (simplified using IS-style alpha coefficients).
Designs steel in X and Y directions separately using strip method.
"""

import math

from .constants import (
    TWO_WAY_ALPHA,
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

# Common bar diameters (mm)
COMMON_BARS = [8, 10, 12, 16, 20, 25, 32]


def _get_alpha(case="interior"):
    """
    Return alpha_x, alpha_y for the specified panel case.
    case: 'interior', 'edge', 'corner'
    """
    case = case.lower()
    if case not in TWO_WAY_ALPHA:
        case = "interior"
    vals = TWO_WAY_ALPHA[case]
    return vals["alpha_x"], vals["alpha_y"]


def design_twoway_slab(
    Lx_m,
    Ly_m,
    panel_case="interior",           # 'interior' | 'edge' | 'corner'
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
    Design a two-way slab panel using coefficient method.
    Returns a dictionary with Mx, My, Ast_x, Ast_y, spacings and warnings.
    """

    # 1) Load per metre strip
    # overall depth for self-weight estimate: assume nominal 150 mm if unknown? Use conservative 150 mm.
    # But here we'll compute self-weight based on an assumed D = 150 mm + cover + bar_dia/2 (simple)
    assumed_D_mm = 150.0 + cover_mm + max(bar_dia_x_mm, bar_dia_y_mm) / 2.0
    self_wt_kN_per_m = slab_self_weight(assumed_D_mm) * strip_width_m

    floor_finish_kN_per_m = floor_finish_kN_m2 * strip_width_m
    live_load_kN_per_m = live_load_kN_m2 * strip_width_m

    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, floor_finish_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, live_load_kN_per_m)  # kN/m (ultimate uniformly distributed load per metre)

    # 2) Get alpha coefficients
    alpha_x, alpha_y = _get_alpha(panel_case)

    # 3) Compute moments (per metre strip)
    # Mx = alpha_x * w * Lx^2 (kN·m per metre)
    Mx_kN_m = alpha_x * wu_kN_per_m * (Lx_m ** 2)
    My_kN_m = alpha_y * wu_kN_per_m * (Ly_m ** 2)

    # convert to Nmm
    Mx_Nmm = moment_kNm_to_Nmm(Mx_kN_m)
    My_Nmm = moment_kNm_to_Nmm(My_kN_m)

    # 4) Choose effective depths (we will use a conservative rule: L/d = 20 for both directions)
    d_x_mm = max((Lx_m * 1000.0) / 20.0, 100.0)
    d_y_mm = max((Ly_m * 1000.0) / 20.0, 100.0)

    b_mm = 1000.0  # per metre strip

    # 5) Solve for Ast in both directions
    ast_x = solve_ast_from_mu(Mx_Nmm, d_x_mm, b_mm=b_mm, fck=fck, fy=fy)
    ast_y = solve_ast_from_mu(My_Nmm, d_y_mm, b_mm=b_mm, fck=fck, fy=fy)

    # 6) Enforce minimum steel
    ast_x_min = MIN_REINFORCEMENT_RATIO * b_mm * d_x_mm
    ast_y_min = MIN_REINFORCEMENT_RATIO * b_mm * d_y_mm

    min_x_flag = False
    min_y_flag = False

    if ast_x < ast_x_min:
        ast_x = ast_x_min
        min_x_flag = True
    if ast_y < ast_y_min:
        ast_y = ast_y_min
        min_y_flag = True

    # 7) Bar selection & spacing for X and Y
    As_x = (math.pi * (bar_dia_x_mm ** 2)) / 4.0
    spacing_x_mm = (As_x * 1000.0) / ast_x
    spacing_x_mm = max(50, int(math.ceil(spacing_x_mm / 5.0) * 5))  # practical rounding to 5 mm, min 50 mm
    spacing_x_mm = min(spacing_x_mm, MAX_BAR_SPACING)
    ast_x_prov = As_x * (1000.0 / spacing_x_mm)

    As_y = (math.pi * (bar_dia_y_mm ** 2)) / 4.0
    spacing_y_mm = (As_y * 1000.0) / ast_y
    spacing_y_mm = max(50, int(math.ceil(spacing_y_mm / 5.0) * 5))
    spacing_y_mm = min(spacing_y_mm, MAX_BAR_SPACING)
    ast_y_prov = As_y * (1000.0 / spacing_y_mm)

    # 8) Warnings
    warnings = []
    if spacing_x_mm > MAX_BAR_SPACING:
        warnings.append(f"X-direction spacing ({spacing_x_mm} mm) exceeds IS max {MAX_BAR_SPACING} mm.")
    if spacing_y_mm > MAX_BAR_SPACING:
        warnings.append(f"Y-direction spacing ({spacing_y_mm} mm) exceeds IS max {MAX_BAR_SPACING} mm.")
    if min_x_flag:
        warnings.append("X-direction steel set to minimum reinforcement.")
    if min_y_flag:
        warnings.append("Y-direction steel set to minimum reinforcement.")

    # deflection heuristic
    if (d_x_mm / (Lx_m * 1000.0)) < (1.0 / 20.0):
        warnings.append("X-direction: effective depth may be small for deflection (d/L < 1/20).")
    if (d_y_mm / (Ly_m * 1000.0)) < (1.0 / 20.0):
        warnings.append("Y-direction: effective depth may be small for deflection (d/L < 1/20).")

    result = {
        "slab_type": "Two-way",
        "panel_case": panel_case,
        "wu_kN_per_m": round(wu_kN_per_m, 3),
        "alpha_x": alpha_x,
        "alpha_y": alpha_y,
        "Mx_kN_m_per_m": round(Mx_kN_m, 3),
        "My_kN_m_per_m": round(My_kN_m, 3),
        "d_x_mm": round(d_x_mm, 1),
        "d_y_mm": round(d_y_mm, 1),
        "Ast_x_req_mm2_per_m": round(ast_x, 2),
        "Ast_x_prov_mm2_per_m": round(ast_x_prov, 2),
        "bar_x_mm": bar_dia_x_mm,
        "spacing_x_mm": int(spacing_x_mm),
        "Ast_y_req_mm2_per_m": round(ast_y, 2),
        "Ast_y_prov_mm2_per_m": round(ast_y_prov, 2),
        "bar_y_mm": bar_dia_y_mm,
        "spacing_y_mm": int(spacing_y_mm),
        "warnings": warnings
    }

    return result

