"""
two_way.py
----------
Clean, deflection-free implementation of IS 456 Two-Way Slab Design
using Table-27 coefficients and IS shear rules.

Features:
- Exposure condition support (cover recommendation only)
- No deflection logic
- Clean bending + shear + minimum steel + bar selection
"""

from typing import Dict, List
import math

from .constants import (
    get_table27_alphas,
    TABLE19_FCK,
    TABLE19_PT,
    TABLE19_TAU_C,
    DEFAULT_WIDTH,
    MIN_REINFORCEMENT_RATIO
)
from .helpers import (
    slab_self_weight,
    total_dead_load,
    factored_load,
)
from .reinforcement import recommend_bars
from .units import moment_kNm_to_Nmm

# Exposure → Recommended nominal cover (IS-456 Table-16)
RECOMMENDED_COVER_BY_EXPOSURE = {
    "Mild": 20,
    "Moderate": 30,
    "Severe": 45,
    "Very Severe": 50,
    "Extreme": 75
}


# -------------------------------------------------------------------
# Simple interpolation used for Table 19 (tau_c)
# -------------------------------------------------------------------
def interp1d(x_points, y_points, x):
    x = max(min(x, x_points[-1]), x_points[0])
    for i in range(len(x_points) - 1):
        if x_points[i] <= x <= x_points[i + 1]:
            x0, x1 = x_points[i], x_points[i + 1]
            y0, y1 = y_points[i], y_points[i + 1]
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return y_points[-1]


# -------------------------------------------------------------------
# Solve Ast from Mu (IS stress block, singly reinforced)
# -------------------------------------------------------------------
def solve_ast_from_mu(Mu_Nmm: float, d_mm: float, fck: float, fy: float, b_mm: float = 1000.0) -> float:
    ast = 1.0
    while ast < 1_000_000.0:
        x = (0.87 * fy * ast) / (0.36 * fck * b_mm)
        if x >= d_mm:
            mu_calc = 1e18
        else:
            mu_calc = 0.87 * fy * ast * (d_mm - 0.42 * x)
        if mu_calc >= Mu_Nmm:
            return ast
        ast += 1.0
    return ast


# -------------------------------------------------------------------
# Interpolate tau_c from Table-19
# -------------------------------------------------------------------
def table19_tau_c(fck: float, pt_percent: float) -> float:
    pt_percent = max(min(pt_percent, TABLE19_PT[-1]), TABLE19_PT[0])

    row_vals = []
    for row in TABLE19_TAU_C:
        row_vals.append(interp1d(TABLE19_PT, row, pt_percent))

    fck = max(min(fck, TABLE19_FCK[-1]), TABLE19_FCK[0])
    return interp1d(TABLE19_FCK, row_vals, fck)


# -------------------------------------------------------------------
# MAIN TWO-WAY DESIGN FUNCTION (CLEAN FINAL VERSION)
# -------------------------------------------------------------------
def design_twoway_slab(
    Lx_m: float,
    Ly_m: float,
    live_load_kN_m2: float = 3.0,
    floor_finish_kN_m2: float = 0.5,
    partitions_kN_per_m: float = 0.0,
    wall_thickness_mm: float = 115.0,
    strip_width_m: float = DEFAULT_WIDTH / 1000.0,
    cover_mm: float = 20.0,
    bar_dia_x_mm: int = 10,
    bar_dia_y_mm: int = 10,
    fck: float = 25.0,
    fy: float = 500.0,
    exposure: str = "Moderate",
    L_div_d: float = 20.0
) -> Dict:

    detailed_steps: List[Dict] = []
    warnings: List[str] = []

    # 0 — Input summary
    detailed_steps.append({
        "title": "Inputs Summary",
        "body": (
            f"Lx = {Lx_m:.3f} m, Ly = {Ly_m:.3f} m\n"
            f"Exposure = {exposure}\n"
            f"Cover = {cover_mm} mm\n"
            f"Bars X/Y = {bar_dia_x_mm}/{bar_dia_y_mm} mm\n"
            f"fck = {fck} MPa, fy = {fy} MPa\n"
            f"Wall thickness = {wall_thickness_mm} mm\n"
        )
    })

    # 1 — Identify short & long spans
    if Ly_m >= Lx_m:
        L_short, L_long = Lx_m, Ly_m
    else:
        L_short, L_long = Ly_m, Lx_m

    ly_lx_ratio = L_long / L_short

    detailed_steps.append({
        "title": "Span Classification",
        "body": f"Short = {L_short:.3f} m, Long = {L_long:.3f} m, ly/lx = {ly_lx_ratio:.3f}"
    })

    # 2 — Depth from L/d
    d_short = max((L_short * 1000.0) / L_div_d, 100)
    d_long = max((L_long * 1000.0) / L_div_d, 100)

    D_short = d_short + cover_mm + bar_dia_x_mm / 2
    D_long = d_long + cover_mm + bar_dia_y_mm / 2
    D_use = max(D_short, D_long)

    detailed_steps.append({
        "title": "Depth Estimation",
        "body": (
            f"d_short = {d_short:.1f} mm, d_long = {d_long:.1f} mm\n"
            f"Overall depth used for self-weight = {D_use:.1f} mm"
        )
    })

    # 3 — Loads
    self_wt = slab_self_weight(D_use) * strip_width_m
    floor_kN = floor_finish_kN_m2 * strip_width_m
    live_kN = live_load_kN_m2 * strip_width_m

    if partitions_kN_per_m == 0:
        partitions_kN_per_m = (wall_thickness_mm / 115.0) * 3.5

    DL = total_dead_load(self_wt, floor_kN, partitions_kN_per_m)
    wu = factored_load(DL, live_kN)

    detailed_steps.append({
        "title": "Load Summary",
        "body": (
            f"Self-weight = {self_wt:.3f} kN/m\n"
            f"DL = {DL:.3f} kN/m, LL = {live_kN:.3f} kN/m\n"
            f"w_u = {wu:.3f} kN/m"
        )
    })

    # 4 — Table-27 coefficients
    alpha_x, alpha_y = get_table27_alphas(ly_lx_ratio)

    detailed_steps.append({
        "title": "Table-27 Coefficients",
        "body": f"alpha_x = {alpha_x:.4f}, alpha_y = {alpha_y:.4f}"
    })

    # 5 — Bending Moments
    Mx = alpha_x * wu * L_short * L_short
    My = alpha_y * wu * L_long * L_long

    MxN = moment_kNm_to_Nmm(Mx)
    MyN = moment_kNm_to_Nmm(My)

    detailed_steps.append({
        "title": "Bending Moments",
        "body": f"Mx = {Mx:.3f} kN-m/m, My = {My:.3f} kN-m/m"
    })

    # 6 — Required Ast
    Ast_x = solve_ast_from_mu(MxN, d_short, fck, fy)
    Ast_y = solve_ast_from_mu(MyN, d_long, fck, fy)

    detailed_steps.append({
        "title": "Required Steel",
        "body": f"Ast_x = {Ast_x:.1f} mm²/m\nAst_y = {Ast_y:.1f} mm²/m"
    })

    # 7 — Minimum reinforcement
    Ast_x_min = MIN_REINFORCEMENT_RATIO * 1000 * d_short
    Ast_y_min = MIN_REINFORCEMENT_RATIO * 1000 * d_long

    if Ast_x < Ast_x_min:
        Ast_x = Ast_x_min
        warnings.append("X-direction: Minimum reinforcement governing.")

    if Ast_y < Ast_y_min:
        Ast_y = Ast_y_min
        warnings.append("Y-direction: Minimum reinforcement governing.")

    # 8 — Bar selection
    rec_x = recommend_bars(Ast_x)
    rec_y = recommend_bars(Ast_y)

    bx = rec_x["recommended"]
    by = rec_y["recommended"]

    detailed_steps.append({
        "title": "Bar Selection",
        "body": (
            f"X: {bx['bar_dia_mm']} mm @ {bx['spacing_mm']} mm → Ast = {bx['Ast_provided_mm2_per_m']:.1f}\n"
            f"Y: {by['bar_dia_mm']} mm @ {by['spacing_mm']} mm → Ast = {by['Ast_provided_mm2_per_m']:.1f}"
        )
    })

    # 9 — Shear check (simple strip method)
    Vu_x = wu * L_short / 2
    Vu_y = wu * L_long / 2

    tau_v_x = (Vu_x * 1000) / (1000 * d_short)
    tau_v_y = (Vu_y * 1000) / (1000 * d_long)

    pt_x = 100 * Ast_x / (1000 * d_short)
    pt_y = 100 * Ast_y / (1000 * d_long)

    tau_c_x = table19_tau_c(fck, pt_x)
    tau_c_y = table19_tau_c(fck, pt_y)

    detailed_steps.append({
        "title": "Shear Check",
        "body": (
            f"τv_x = {tau_v_x:.4f}, τc_x = {tau_c_x:.4f}\n"
            f"τv_y = {tau_v_y:.4f}, τc_y = {tau_c_y:.4f}"
        )
    })

    if tau_v_x > tau_c_x:
        warnings.append("Shear failure in X-direction. Increase depth.")
    if tau_v_y > tau_c_y:
        warnings.append("Shear failure in Y-direction. Increase depth.")

    # 10 — Package results
    result = {
        "slab_type": "Two-Way (IS 456 Table-27)",
        "Lx_m": round(Lx_m, 3),
        "Ly_m": round(Ly_m, 3),

        "wu_kN_per_m": round(wu, 3),

        "alpha_x": round(alpha_x, 5),
        "alpha_y": round(alpha_y, 5),

        "Mx_kN_m_per_m": round(Mx, 3),
        "My_kN_m_per_m": round(My, 3),

        "d_short_mm": round(d_short, 1),
        "d_long_mm": round(d_long, 1),

        "Ast_req_x_mm2_per_m": round(Ast_x, 1),
        "Ast_req_y_mm2_per_m": round(Ast_y, 1),

        "Ast_prov_x_mm2_per_m": round(bx["Ast_provided_mm2_per_m"], 1),
        "Ast_prov_y_mm2_per_m": round(by["Ast_provided_mm2_per_m"], 1),

        "bar_x_mm": bx["bar_dia_mm"],
        "spacing_x_mm": bx["spacing_mm"],

        "bar_y_mm": by["bar_dia_mm"],
        "spacing_y_mm": by["spacing_mm"],

        "tau_v_x": round(tau_v_x, 4),
        "tau_c_x": round(tau_c_x, 4),

        "tau_v_y": round(tau_v_y, 4),
        "tau_c_y": round(tau_c_y, 4),

        "exposure_condition": exposure,
        "recommended_cover_mm": RECOMMENDED_COVER_BY_EXPOSURE.get(exposure),

        "warnings": warnings,
        "detailed_steps": detailed_steps,
    }

    return result
