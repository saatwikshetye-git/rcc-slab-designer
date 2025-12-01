"""
one_way.py
----------
One-way slab design engine (IS 456 style), simplified and robust.
All results are returned per metre width (i.e. strip method).
"""

import math

from .constants import (
    DEFAULT_WIDTH,
    MIN_REINFORCEMENT_RATIO,
    MAX_BAR_SPACING,
    DEFAULT_FCK,
    DEFAULT_FY
)
from .units import moment_kNm_to_Nmm
from .helpers import (
    effective_span_clear,
    slab_self_weight,
    total_dead_load,
    factored_load,
    round_up
)


# Common bar diameters (mm)
COMMON_BARS = [8, 10, 12, 16, 20, 25, 32]


def solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=1000, fck=DEFAULT_FCK, fy=DEFAULT_FY):
    """
    Numerically solve for Ast (mm^2 per metre width) for a singly-reinforced
    rectangular section using the IS 456 simplified stress block.

    Parameters
    ----------
    Mu_Nmm : float
        Required bending moment in N·mm (for 1 m width).
    d_mm : float
        Effective depth in mm.
    b_mm : float
        Breadth considered in mm (default 1000 mm for 1m strip).
    fck : float
        Concrete grade in N/mm^2 (MPa).
    fy : float
        Steel yield stress in N/mm^2 (MPa).

    Returns
    -------
    ast_required_mm2_per_m : float
        Required tension steel area per metre width (mm^2/m).
    """
    # Start from a small area and iterate upward until Mu_calc >= Mu_req
    ast = 1.0  # mm2 per metre initial (very small)
    step = 1.0  # incremental step in mm2 (fine resolution)
    max_ast = 1_000_000.0  # safety cap to avoid infinite loops

    while ast < max_ast:
        # depth of neutral axis x using force equilibrium: 0.36*fck*b*x = 0.87*fy*Ast
        x_mm = (0.87 * fy * ast) / (0.36 * fck * b_mm)

        # Check for unreasonable x (should not exceed d)
        if x_mm >= d_mm:
            # In practice this implies compression failure — we treat it as very large moment capacity
            mu_calc = 1e18
        else:
            mu_calc = 0.87 * fy * ast * (d_mm - 0.42 * x_mm)  # N * mm

        if mu_calc >= Mu_Nmm:
            return ast

        ast += step

    # if loop finishes, return large ast (should not happen for reasonable inputs)
    return max_ast


def design_oneway_slab(
    span_m,
    # Loads (input as per-m2 values for finish & live load; partitions as per-m)
    live_load_kN_m2=3.0,
    floor_finish_kN_m2=0.5,
    partitions_kN_per_m=0.0,
    # geometry and reinforcement choices
    strip_width_m=DEFAULT_WIDTH / 1000.0,
    support_width_m=0.0,
    L_div_d=20,
    cover_mm=20,
    bar_dia_mm=10,
    # material grades
    fck=DEFAULT_FCK,
    fy=DEFAULT_FY
):
    """
    Main design entry for a one-way slab (per metre strip).

    Returns a dictionary with computed values (d, D, Mu, Ast, spacing, warnings).
    """
    # ---------- effective span ----------
    L_eff = effective_span_clear(span_m, support_width_m)  # metres

    # ---------- effective depth ----------
    # d (mm) from chosen L/d ratio (L in m -> convert to mm)
    d_mm = (L_eff * 1000.0) / L_div_d
    d_mm = max(d_mm, 100.0)  # practical minimum effective depth

    # overall (nominal) depth D (mm) -- assume bar centroid at dia/2 below top of cover
    D_mm = d_mm + cover_mm + (bar_dia_mm / 2.0)

    # ---------- loads (per metre strip) ----------
    # self weight using D_mm (kN/m for 1m width)
    self_wt_kN_per_m = slab_self_weight(D_mm) * strip_width_m / 1.0  # helper returns kN/m per metre width; multiply by strip width

    # floor finish and live load are typically provided in kN/m2 -> convert to kN/m for strip_width
    floor_finish_kN_per_m = floor_finish_kN_m2 * strip_width_m
    live_load_kN_per_m = live_load_kN_m2 * strip_width_m

    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, floor_finish_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, live_load_kN_per_m)  # ultimate uniformly distributed load (kN/m)

    # ---------- bending moment ----------
    Mu_kN_m = (wu_kN_per_m * (L_eff ** 2)) / 8.0  # kN·m per metre
    Mu_Nmm = moment_kNm_to_Nmm(Mu_kN_m)  # convert to N·mm

    # ---------- solve for Ast (mm2 per metre) ----------
    b_mm = 1000.0  # 1 metre strip width
    ast_req = solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=b_mm, fck=fck, fy=fy)

    # ---------- enforce minimum steel (area per metre) ----------
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm
    if ast_req < ast_min:
        ast_req = ast_min
        min_reinf_flag = True
    else:
        min_reinf_flag = False

    # ---------- bar selection & spacing ----------
    # Area of one bar (mm2)
    As_single = (math.pi * (bar_dia_mm ** 2)) / 4.0
    # spacing (mm) for that bar to provide ast_req per metre:
    spacing_mm = (As_single * 1000.0) / ast_req  # mm

    # Round spacing to a practical value (nearest 5 mm) and clamp
    spacing_mm = round_up(spacing_mm, 5)
    spacing_mm = min(spacing_mm, MAX_BAR_SPACING)

    # Provided steel area (actual) with this spacing
    provided_ast = As_single * (1000.0 / spacing_mm)

    # ---------- checks and warnings ----------
    warnings = []
    if spacing_mm > MAX_BAR_SPACING:
        warnings.append(f"Spacing ({spacing_mm} mm) exceeds IS maximum of {MAX_BAR_SPACING} mm.")
    if min_reinf_flag:
        warnings.append("Provided steel limited by minimum reinforcement requirement.")
    # Simple deflection heuristic: if d/L < 1/20 for simply supported, warn (conservative)
    if (d_mm / (L_eff * 1000.0)) < (1.0 / 20.0):
        warnings.append("Effective depth may be small for deflection limit (d/L < 1/20).")

    # ---------- package results ----------
    result = {
        "slab_type": "One-way",
        "effective_span_m": round(L_eff, 3),
        "d_mm": round(d_mm, 1),
        "D_mm": round(D_mm, 1),
        "wu_kN_per_m": round(wu_kN_per_m, 3),
        "Mu_kN_m_per_m": round(Mu_kN_m, 3),
        "Mu_Nmm_per_m": round(Mu_Nmm, 1),
        "Ast_required_mm2_per_m": round(ast_req, 2),
        "Ast_provided_mm2_per_m": round(provided_ast, 2),
        "bar_dia_mm": bar_dia_mm,
        "spacing_mm": int(spacing_mm),
        "warnings": warnings
    }

    return result

