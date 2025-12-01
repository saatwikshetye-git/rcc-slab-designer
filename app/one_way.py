"""
one_way.py
----------
IS 456:2000 Compliant One-Way Slab Design (per metre strip)
Corrected version with:
- Proper effective span formula (Clause 22.2)
- Correct load handling
- Correct moment & Ast calculation
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
    slab_self_weight,
    total_dead_load,
    factored_load,
    round_up
)


# ---------------------------------------------------------
# AST SOLVER BASED ON IS STRESS BLOCK
# ---------------------------------------------------------

def solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=1000, fck=DEFAULT_FCK, fy=DEFAULT_FY):
    """
    Iteratively solve Ast using IS 456 stress block.
    Singly reinforced section only.
    """
    ast = 1.0      # start small
    step = 1.0     # mm² increments
    max_ast = 1_000_000.0

    while ast < max_ast:
        # neutral axis depth
        x_mm = (0.87 * fy * ast) / (0.36 * fck * b_mm)

        if x_mm >= d_mm:
            mu_calc = 1e18   # compression failure region; treat as huge
        else:
            mu_calc = 0.87 * fy * ast * (d_mm - 0.42 * x_mm)

        if mu_calc >= Mu_Nmm:
            return ast

        ast += step

    return max_ast


# ---------------------------------------------------------
# MAIN ONE-WAY SLAB DESIGN
# ---------------------------------------------------------

def design_oneway_slab(
    clear_span_m,
    live_load_kN_m2=3.0,
    floor_finish_kN_m2=0.5,
    partitions_kN_per_m=0.0,
    strip_width_m=DEFAULT_WIDTH / 1000.0,
    support_width_m=0.0,
    L_div_d=20,
    cover_mm=20,
    bar_dia_mm=10,
    fck=DEFAULT_FCK,
    fy=DEFAULT_FY
):
    """
    Correct IS 456 one-way slab design per metre strip.

    clear_span_m → CLEAR span in metres (as per UI)
    support_width_m → width of the beam/wall support in metres
    """

    # ---------------------------------------------------------
    # 1) EFFECTIVE SPAN (Clause 22.2)
    # ---------------------------------------------------------
    # effective_depth d required first (rough, using span/Ld with clear span)
    d_initial = max((clear_span_m * 1000.0) / L_div_d, 100)

    centre_to_centre = clear_span_m + support_width_m
    clear_plus_d     = clear_span_m + (d_initial / 1000.0)

    # IS formula: Effective span = min( clear span + d, centre-to-centre span )
    L_eff = min(clear_plus_d, centre_to_centre)

    # recompute effective depth using correct effective span
    d_mm = max((L_eff * 1000.0) / L_div_d, 100.0)

    # Overall depth
    D_mm = d_mm + cover_mm + bar_dia_mm / 2.0

    # ---------------------------------------------------------
    # 2) LOAD CALCULATIONS (per metre strip)
    # ---------------------------------------------------------

    # Self-weight based on overall depth
    self_wt_kN_per_m = slab_self_weight(D_mm) * strip_width_m

    # Floor finish & live load (kN/m² → kN/m)
    FF_kN_per_m = floor_finish_kN_m2 * strip_width_m
    LL_kN_per_m = live_load_kN_m2 * strip_width_m

    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, FF_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, LL_kN_per_m)

    # ---------------------------------------------------------
    # 3) BENDING MOMENT (IS 456 simply supported)
    # ---------------------------------------------------------

    Mu_kN_m = wu_kN_per_m * (L_eff ** 2) / 8.0
    Mu_Nmm = moment_kNm_to_Nmm(Mu_kN_m)

    # ---------------------------------------------------------
    # 4) AST CALCULATION
    # ---------------------------------------------------------

    b_mm = 1000.0
    ast_req = solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=b_mm, fck=fck, fy=fy)

    # Minimum reinforcement check
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm
    min_flag = False
    if ast_req < ast_min:
        ast_req = ast_min
        min_flag = True

    # ---------------------------------------------------------
    # 5) STEEL SPACING
    # ---------------------------------------------------------

    As_bar = (math.pi * (bar_dia_mm**2)) / 4.0
    spacing_mm = (As_bar * 1000.0) / ast_req

    spacing_mm = round_up(spacing_mm, 5)
    spacing_mm = min(spacing_mm, MAX_BAR_SPACING)

    provided_ast = As_bar * (1000.0 / spacing_mm)

    # ---------------------------------------------------------
    # 6) WARNINGS
    # ---------------------------------------------------------
    warnings = []

    if spacing_mm > MAX_BAR_SPACING:
        warnings.append(f"Spacing {spacing_mm} mm exceeds IS max {MAX_BAR_SPACING} mm.")

    if min_flag:
        warnings.append("Ast governed by minimum reinforcement requirement (0.12%).")

    if (d_mm / (L_eff * 1000.0)) < (1/20):
        warnings.append("Effective depth may be inadequate for deflection (d/L < 1/20).")

    # ---------------------------------------------------------
    # 7) RETURN RESULTS
    # ---------------------------------------------------------

    return {
        "slab_type": "One-way",
        "clear_span_m": round(clear_span_m, 3),
        "effective_span_m": round(L_eff, 3),
        "d_mm": round(d_mm, 1),
        "D_mm": round(D_mm, 1),
        "dead_load_kN_per_m": round(dead_load_kN_per_m, 3),
        "wu_kN_per_m": round(wu_kN_per_m, 3),
        "Mu_kN_m_per_m": round(Mu_kN_m, 3),
        "Ast_required_mm2_per_m": round(ast_req, 2),
        "Ast_provided_mm2_per_m": round(provided_ast, 2),
        "bar_dia_mm": bar_dia_mm,
        "spacing_mm": int(spacing_mm),
        "warnings": warnings
    }
