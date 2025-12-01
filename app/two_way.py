"""
two_way.py

Two-way slab design (IS Table 27 method).
Deflection logic removed. Focus: moments (Table 27), depth sizing by L/d,
flexural design, minimum steel, cracking indicator and shear (Table 19).
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
    effective_span_clear,
)
from .reinforcement import recommend_bars, area_of_bar_mm2
from .units import moment_kNm_to_Nmm
from .constants import interp1d as _interp1d  # local interp helper for table19

# Local helpers
def interp_table19_tau_c(fck: float, p_t_percent: float) -> float:
    pt = max(min(p_t_percent, TABLE19_PT[-1]), TABLE19_PT[0])
    row_vals = []
    for row in TABLE19_TAU_C:
        tau_at_pt = _interp1d(TABLE19_PT, row, pt)
        row_vals.append(tau_at_pt)
    fck_clamped = max(min(fck, TABLE19_FCK[-1]), TABLE19_FCK[0])
    tau_final = _interp1d(TABLE19_FCK, row_vals, fck_clamped)
    return float(tau_final)


def solve_ast_from_mu(Mu_Nmm: float, d_mm: float, b_mm: float = 1000.0, fck: float = 25.0, fy: float = 500.0) -> float:
    ast = 1.0
    step = 1.0
    max_ast = 1_000_000.0
    while ast < max_ast:
        x_mm = (0.87 * fy * ast) / (0.36 * fck * b_mm)
        if x_mm >= d_mm:
            mu_calc = 1e18
        else:
            mu_calc = 0.87 * fy * ast * (d_mm - 0.42 * x_mm)
        if mu_calc >= Mu_Nmm:
            return ast
        ast += step
    return max_ast


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
    L_div_d: float = 20.0
) -> Dict:
    detailed_steps: List[Dict] = []
    warnings: List[str] = []

    detailed_steps.append({
        "title": "Inputs summary",
        "body": (
            f"Lx = {Lx_m:.3f} m, Ly = {Ly_m:.3f} m\n"
            f"Wall thickness = {wall_thickness_mm:.1f} mm\n"
            f"Live load = {live_load_kN_m2:.3f} kN/m², Floor finish = {floor_finish_kN_m2:.3f} kN/m²\n"
            f"Partitions (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"fck = {fck} MPa, fy = {fy} MPa, cover = {cover_mm} mm\n"
            f"Bar dia X = {bar_dia_x_mm} mm, Bar dia Y = {bar_dia_y_mm} mm"
        )
    })

    # Short/long classification
    if Ly_m >= Lx_m:
        L_short = Lx_m
        L_long = Ly_m
        ly_lx_ratio = Ly_m / Lx_m
    else:
        L_short = Ly_m
        L_long = Lx_m
        ly_lx_ratio = Lx_m / Ly_m

    detailed_steps.append({
        "title": "Span classification",
        "body": f"Short span = {L_short:.3f} m, Long span = {L_long:.3f} m, ly/lx = {ly_lx_ratio:.4f}"
    })

    # Initial depth sizing
    d_short_mm = max((L_short * 1000.0) / L_div_d, 100.0)
    d_long_mm = max((L_long * 1000.0) / L_div_d, 100.0)
    detailed_steps.append({
        "title": "Initial effective depths (from L/d)",
        "body": f"d_short = {d_short_mm:.1f} mm, d_long = {d_long_mm:.1f} mm (using L/d = {L_div_d})"
    })

    # Overall D for self weight
    D_short_mm = d_short_mm + cover_mm + (bar_dia_x_mm / 2.0)
    D_long_mm = d_long_mm + cover_mm + (bar_dia_y_mm / 2.0)
    assumed_D_mm = max(D_short_mm, D_long_mm)
    detailed_steps.append({
        "title": "Overall depth for self-weight",
        "body": f"D_short = {D_short_mm:.1f} mm, D_long = {D_long_mm:.1f} mm -> assumed D = {assumed_D_mm:.1f} mm"
    })

    # Loads
    self_wt_kN_per_m = slab_self_weight(assumed_D_mm) * strip_width_m
    floor_kN_per_m = floor_finish_kN_m2 * strip_width_m
    live_kN_per_m = live_load_kN_m2 * strip_width_m

    if partitions_kN_per_m <= 0.0 and wall_thickness_mm > 0.0:
        partitions_kN_per_m = (wall_thickness_mm / 115.0) * 3.5

    dl_kN_per_m = total_dead_load(self_wt_kN_per_m, floor_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dl_kN_per_m, live_kN_per_m)

    detailed_steps.append({
        "title": "Loads (per metre strip)",
        "body": (
            f"Self-weight = {self_wt_kN_per_m:.3f} kN/m, Floor finish = {floor_kN_per_m:.3f} kN/m, "
            f"Live = {live_kN_per_m:.3f} kN/m, Partitions = {partitions_kN_per_m:.3f} kN/m\n"
            f"DL = {dl_kN_per_m:.3f} kN/m, Factored w_u = {wu_kN_per_m:.3f} kN/m"
        )
    })

    # Table 27 coefficients
    alpha_x, alpha_y = get_table27_alphas(ly_lx_ratio)
    detailed_steps.append({
        "title": "Table 27 coefficients",
        "body": f"Interpolated alpha_x = {alpha_x:.6f}, alpha_y = {alpha_y:.6f} (for ly/lx = {ly_lx_ratio:.4f})"
    })

    # Moments
    Mx_kN_m = alpha_x * wu_kN_per_m * (L_short ** 2)
    My_kN_m = alpha_y * wu_kN_per_m * (L_long ** 2)
    Mx_Nmm = moment_kNm_to_Nmm(Mx_kN_m)
    My_Nmm = moment_kNm_to_Nmm(My_kN_m)
    detailed_steps.append({
        "title": "Bending moments (per metre)",
        "body": f"Mx = {Mx_kN_m:.4f} kN·m/m    My = {My_kN_m:.4f} kN·m/m"
    })

    # Flexural design for both directions
    ast_short_req = solve_ast_from_mu(Mx_Nmm, d_short_mm, b_mm=1000.0, fck=fck, fy=fy)
    ast_long_req = solve_ast_from_mu(My_Nmm, d_long_mm, b_mm=1000.0, fck=fck, fy=fy)
    detailed_steps.append({
        "title": "Flexural design (Ast required)",
        "body": f"Ast_short_required = {ast_short_req:.2f} mm²/m    Ast_long_required = {ast_long_req:.2f} mm²/m"
    })

    # Minimum reinforcement
    ast_short_min = MIN_REINFORCEMENT_RATIO * 1000.0 * d_short_mm
    ast_long_min = MIN_REINFORCEMENT_RATIO * 1000.0 * d_long_mm
    if ast_short_req < ast_short_min:
        ast_short_req = ast_short_min
        warnings.append("Short-direction: Ast limited to minimum reinforcement (IS clause).")
    if ast_long_req < ast_long_min:
        ast_long_req = ast_long_min
        warnings.append("Long-direction: Ast limited to minimum reinforcement (IS clause).")

    detailed_steps.append({
        "title": "Minimum reinforcement (IS clause)",
        "body": f"Ast_short_min = {ast_short_min:.2f}, Ast_long_min = {ast_long_min:.2f}"
    })

    # Bar selection
    rec_short = recommend_bars(ast_short_req)
    rec_long = recommend_bars(ast_long_req)
    chosen_short = rec_short["recommended"]
    chosen_long = rec_long["recommended"]

    ast_short_prov = chosen_short["Ast_provided_mm2_per_m"]
    ast_long_prov = chosen_long["Ast_provided_mm2_per_m"]

    detailed_steps.append({
        "title": "Bar selection (recommendation)",
        "body": (
            f"Short-direction -> dia {chosen_short['bar_dia_mm']} mm @ {chosen_short['spacing_mm']} mm => Ast_prov = {ast_short_prov:.2f} mm²/m\n"
            f"Long-direction  -> dia {chosen_long['bar_dia_mm']} mm @ {chosen_long['spacing_mm']} mm => Ast_prov = {ast_long_prov:.2f} mm²/m"
        )
    })

    # Cracking indicator
    ptx = 100.0 * ast_short_req / (1000.0 * d_short_mm)
    pty = 100.0 * ast_long_req / (1000.0 * d_long_mm)
    crack_notes = []
    if ptx < 0.15:
        crack_notes.append("Short-direction: low steel ratio (<0.15%) — cracking likely; review cover/steel")
    if pty < 0.15:
        crack_notes.append("Long-direction: low steel ratio (<0.15%) — cracking likely; review cover/steel")
    if crack_notes:
        warnings.extend(crack_notes)
    detailed_steps.append({
        "title": "Crack check indicator",
        "body": f"p_t_x = {ptx:.5f} %, p_t_y = {pty:.5f} %\nNotes: {'; '.join(crack_notes) if crack_notes else 'OK (indicator)'}"
    })

    # Shear checks (strip approx)
    Vu_short_kN = wu_kN_per_m * L_short / 2.0
    Vu_long_kN = wu_kN_per_m * L_long / 2.0
    Vu_short_N = Vu_short_kN * 1000.0
    Vu_long_N = Vu_long_kN * 1000.0
    tau_v_short = Vu_short_N / (1000.0 * d_short_mm)
    tau_v_long = Vu_long_N / (1000.0 * d_long_mm)

    tau_c_short = interp_table19_tau_c(fck, 100.0 * ast_short_req / (1000.0 * d_short_mm))
    tau_c_long = interp_table19_tau_c(fck, 100.0 * ast_long_req / (1000.0 * d_long_mm))

    detailed_steps.append({
        "title": "Shear checks (strip approximation)",
        "body": (
            f"Short: Vu = {Vu_short_kN:.3f} kN -> τv = {tau_v_short:.4f} N/mm², τc = {tau_c_short:.4f} N/mm²\n"
            f"Long : Vu = {Vu_long_kN:.3f} kN -> τv = {tau_v_long:.4f} N/mm², τc = {tau_c_long:.4f} N/mm²"
        )
    })

    if tau_v_short > tau_c_short:
        warnings.append("Short-direction: τv > τc (Table 19) — provide shear reinforcement or increase depth.")
    if tau_v_long > tau_c_long:
        warnings.append("Long-direction: τv > τc (Table 19) — provide shear reinforcement or increase depth.")

    # Final packaging
    result = {
        "slab_type": "Two-way (IS Table 27 method)",
        "ly_lx_ratio": round(ly_lx_ratio, 4),
        "wu_kN_per_m": round(wu_kN_per_m, 4),
        "alpha_x": round(alpha_x, 6),
        "alpha_y": round(alpha_y, 6),
        "L_short_m": round(L_short, 3),
        "L_long_m": round(L_long, 3),
        "Mx_kN_m_per_m": round(Mx_kN_m, 4),
        "My_kN_m_per_m": round(My_kN_m, 4),
        "d_short_mm": round(d_short_mm, 2),
        "d_long_mm": round(d_long_mm, 2),
        "Ast_short_req_mm2_per_m": round(ast_short_req, 2),
        "Ast_short_prov_mm2_per_m": round(ast_short_prov, 2),
        "spacing_short_mm": int(chosen_short["spacing_mm"]) if chosen_short["spacing_mm"] else None,
        "Ast_long_req_mm2_per_m": round(ast_long_req, 2),
        "Ast_long_prov_mm2_per_m": round(ast_long_prov, 2),
        "spacing_long_mm": int(chosen_long["spacing_mm"]) if chosen_long["spacing_mm"] else None,
        "tau_v_short_N_per_mm2": round(tau_v_short, 5),
        "tau_c_short_N_per_mm2": round(tau_c_short, 5),
        "tau_v_long_N_per_mm2": round(tau_v_long, 5),
        "tau_c_long_N_per_mm2": round(tau_c_long, 5),
        "p_t_x_percent": round(ptx, 6),
        "p_t_y_percent": round(pty, 6),
        "fck": fck,
        "fy": fy,
        "cover_mm": cover_mm,
        "warnings": warnings,
        "detailed_steps": detailed_steps
    }

    return result
