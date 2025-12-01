"""
two_way.py
Two-way slab design (Table 27 method) following your specified procedure.
This implementation:
- interpolates Table 27 alpha coefficients
- computes effective spans (1-step iteration)
- computes factored load and moments
- solves Ast using IS stress block solver (from one_way.solve_ast_from_mu)
- enforces minimum steel
- recommends bars via reinforcement.recommend_bars
- checks shear using compute_tau_c_IS (from one_way)
- prepares a detailed_steps list for UI display

Deflection finalization is done only when IS Fig.4/Fig.5 data are embedded; otherwise it is flagged.
"""

import math
from typing import Dict, List

from .constants import get_table27_alphas, DEFAULT_WIDTH, MIN_REINFORCEMENT_RATIO, MAX_BAR_SPACING
from .one_way import solve_ast_from_mu, compute_tau_c_IS
from .helpers import slab_self_weight, total_dead_load, factored_load
from .reinforcement import recommend_bars
from .units import moment_kNm_to_Nmm


def design_twoway_slab(
    Lx_m: float,
    Ly_m: float,
    wall_thickness_mm: float = 115.0,
    live_load_kN_m2: float = 3.0,
    floor_finish_kN_m2: float = 0.5,
    partitions_kN_per_m: float = 0.0,
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

    # Input summary
    detailed_steps.append({"title": "Inputs summary",
                           "body": (f"Lx={Lx_m} m, Ly={Ly_m} m\n"
                                    f"Wall thickness={wall_thickness_mm} mm\n"
                                    f"Live load={live_load_kN_m2} kN/m², Floor finish={floor_finish_kN_m2} kN/m²\n"
                                    f"fck={fck} MPa, fy={fy} MPa\n"
                                    f"Cover={cover_mm} mm, bar X={bar_dia_x_mm} mm, bar Y={bar_dia_y_mm} mm")})

    # classify short/long
    if Ly_m >= Lx_m:
        L_short = Lx_m
        L_long = Ly_m
    else:
        L_short = Ly_m
        L_long = Lx_m

    ly_lx_ratio = L_long / L_short
    detailed_steps.append({"title": "Span classification", "body": f"L_short={L_short} m, L_long={L_long} m, ly/lx={ly_lx_ratio:.4f}"})

    # initial d from L/d
    d_short_init = max((L_short * 1000.0) / L_div_d, 100.0)
    d_long_init = max((L_long * 1000.0) / L_div_d, 100.0)
    detailed_steps.append({"title": "Initial effective depth (from L/d)", "body": f"d_short_init={d_short_init:.1f} mm, d_long_init={d_long_init:.1f} mm"})

    # effective span one-step iteration (clear + d vs centre to centre)
    clear_plus_d_short = L_short + d_short_init/1000.0
    L_eff_short = min(clear_plus_d_short, L_short)
    clear_plus_d_long = L_long + d_long_init/1000.0
    L_eff_long = min(clear_plus_d_long, L_long)

    d_short = max((L_eff_short * 1000.0) / L_div_d, 100.0)
    d_long = max((L_eff_long * 1000.0) / L_div_d, 100.0)

    D_short = d_short + cover_mm + (bar_dia_x_mm / 2.0)
    D_long = d_long + cover_mm + (bar_dia_y_mm / 2.0)

    detailed_steps.append({"title": "Effective span and final depths",
                           "body": f"L_eff_short={L_eff_short:.3f} m, d_short={d_short:.1f} mm, D_short={D_short:.1f} mm\n"
                                   f"L_eff_long={L_eff_long:.3f} m, d_long={d_long:.1f} mm, D_long={D_long:.1f} mm"})

    # loads
    assumed_D = max(D_short, D_long)
    self_wt = slab_self_weight(assumed_D) * strip_width_m
    floor_kN_m = floor_finish_kN_m2 * strip_width_m
    live_kN_m = live_load_kN_m2 * strip_width_m

    if partitions_kN_per_m <= 0.0 and wall_thickness_mm > 0:
        partitions_kN_per_m = (wall_thickness_mm / 115.0) * 3.5

    dl = total_dead_load(self_wt, floor_kN_m, partitions_kN_per_m)
    wu = factored_load(dl, live_kN_m)

    detailed_steps.append({"title": "Loads",
                           "body": f"Assumed D={assumed_D:.1f} mm -> self weight={self_wt:.3f} kN/m\n"
                                   f"Floor/m = {floor_kN_m:.3f} kN/m, Live/m = {live_kN_m:.3f} kN/m, Partitions = {partitions_kN_per_m:.3f} kN/m\n"
                                   f"DL={dl:.3f} kN/m, w_u={wu:.3f} kN/m"})

    # Table 27 interpolation
    alpha_x, alpha_y = get_table27_alphas(ly_lx_ratio)
    Mx = alpha_x * wu * (L_short ** 2)
    My = alpha_y * wu * (L_long ** 2)
    Mx_Nmm = moment_kNm_to_Nmm(Mx)
    My_Nmm = moment_kNm_to_Nmm(My)

    detailed_steps.append({"title": "Moments (Table 27 interpolation)",
                           "body": f"alpha_x={alpha_x:.6f}, alpha_y={alpha_y:.6f}\n"
                                   f"Mx={Mx:.4f} kN·m/m, My={My:.4f} kN·m/m"})

    # solve for Ast
    b = 1000.0
    ast_short_req = solve_ast_from_mu(Mx_Nmm, d_short, b_mm=b, fck=fck, fy=fy)
    ast_long_req = solve_ast_from_mu(My_Nmm, d_long, b_mm=b, fck=fck, fy=fy)

    detailed_steps.append({"title": "Required Ast",
                           "body": f"Ast_short_req={ast_short_req:.2f} mm²/m, Ast_long_req={ast_long_req:.2f} mm²/m"})

    # min steel
    ast_short_min = MIN_REINFORCEMENT_RATIO * b * d_short
    ast_long_min = MIN_REINFORCEMENT_RATIO * b * d_long
    short_min = False
    long_min = False
    if ast_short_req < ast_short_min:
        ast_short_req = ast_short_min
        short_min = True
    if ast_long_req < ast_long_min:
        ast_long_req = ast_long_min
        long_min = True

    detailed_steps.append({"title": "Minimum reinforcement (IS clause)",
                           "body": f"Ast_short_min={ast_short_min:.2f}, Ast_long_min={ast_long_min:.2f}\n"
                                   f"Short_min_applied={short_min}, Long_min_applied={long_min}"})

    # bar recommendations
    rec_x = recommend_bars(ast_short_req)
    rec_y = recommend_bars(ast_long_req)
    chosen_x = rec_x["recommended"]
    chosen_y = rec_y["recommended"]
    ast_x_prov = chosen_x["Ast_provided_mm2_per_m"]
    ast_y_prov = chosen_y["Ast_provided_mm2_per_m"]

    detailed_steps.append({"title": "Bar recommendations",
                           "body": f"X: dia={chosen_x['bar_dia_mm']} mm, spacing={chosen_x['spacing_mm']} mm, Ast_prov={ast_x_prov}\n"
                                   f"Y: dia={chosen_y['bar_dia_mm']} mm, spacing={chosen_y['spacing_mm']} mm, Ast_prov={ast_y_prov}"})

    # cracking indicator
    ptx = 100.0 * ast_short_req / (b * d_short)
    pty = 100.0 * ast_long_req / (b * d_long)
    crack_notes = []
    if ptx < 0.20:
        crack_notes.append("X: low steel ratio; check cracking")
    if pty < 0.20:
        crack_notes.append("Y: low steel ratio; check cracking")

    detailed_steps.append({"title": "Crack checks (indicator)",
                           "body": f"p_t_x={ptx:.4f} %, p_t_y={pty:.4f} %\nNotes: {'; '.join(crack_notes) if crack_notes else 'OK'}"})
    if crack_notes:
        warnings += crack_notes

    # Shear (conservative strip check)
    Vu_short_kN = wu * L_short / 2.0
    Vu_long_kN = wu * L_long / 2.0
    Vu_short_N = Vu_short_kN * 1000.0
    Vu_long_N = Vu_long_kN * 1000.0
    tau_v_short = Vu_short_N / (b * d_short)
    tau_v_long = Vu_long_N / (b * d_long)
    tau_c_short = compute_tau_c_IS(fck=fck, ast_mm2_per_m=ast_short_req, b_mm=b, d_mm=d_short)
    tau_c_long = compute_tau_c_IS(fck=fck, ast_mm2_per_m=ast_long_req, b_mm=b, d_mm=d_long)

    detailed_steps.append({"title": "Shear checks",
                           "body": f"Short: Vu={Vu_short_kN:.3f} kN, τv={tau_v_short:.4f} N/mm², τc={tau_c_short:.4f} N/mm²\n"
                                   f"Long:  Vu={Vu_long_kN:.3f} kN, τv={tau_v_long:.4f} N/mm², τc={tau_c_long:.4f} N/mm²"})
    if tau_v_short > tau_c_short:
        warnings.append("Short-direction: τv > τc -> provide shear reinforcement or redesign")
    if tau_v_long > tau_c_long:
        warnings.append("Long-direction: τv > τc -> provide shear reinforcement or redesign")

    # Deflection: flag (requires Fig.4/Fig.5). We provide p_t values for lookup.
    detailed_steps.append({"title": "Deflection check (requires Fig.4/Fig.5)",
                           "body": f"p_t_x={ptx:.6f} %, p_t_y={pty:.6f} %. Fig.4/Fig.5 interpolation required to determine allowable L/d."})
    warnings.append("Deflection check not completed: IS Fig.4/Fig.5 modifiers required. Ask to digitize them to enable final check.")

    # package results - mapping back to X/Y naming assuming Lx input is X
    result = {
        "slab_type": "Two-way (IS Table 27)",
        "ly_lx_ratio": round(ly_lx_ratio, 4),
        "wu_kN_per_m": round(wu, 4),
        "alpha_x": round(alpha_x, 6),
        "alpha_y": round(alpha_y, 6),
        "L_short_m": round(L_short, 3),
        "L_long_m": round(L_long, 3),
        "Mx_kN_m_per_m": round(Mx, 4),
        "My_kN_m_per_m": round(My, 4),
        "d_short_mm": round(d_short, 2),
        "d_long_mm": round(d_long, 2),
        "Ast_short_req_mm2_per_m": round(ast_short_req, 2),
        "Ast_short_prov_mm2_per_m": round(ast_x_prov, 2),
        "spacing_short_mm": int(chosen_x["spacing_mm"]) if chosen_x["spacing_mm"] else None,
        "Ast_long_req_mm2_per_m": round(ast_long_req, 2),
        "Ast_long_prov_mm2_per_m": round(ast_y_prov, 2),
        "spacing_long_mm": int(chosen_y["spacing_mm"]) if chosen_y["spacing_mm"] else None,
        "tau_v_short_N_per_mm2": round(tau_v_short, 4),
        "tau_c_short_N_per_mm2": round(tau_c_short, 4),
        "tau_v_long_N_per_mm2": round(tau_v_long, 4),
        "tau_c_long_N_per_mm2": round(tau_c_long, 4),
        "p_t_x_percent": round(ptx, 6),
        "p_t_y_percent": round(pty, 6),
        "deflection_check": "REQUIRES_FIG4_FIG5",
        "fck": fck,
        "fy": fy,
        "cover_mm": cover_mm,
        "warnings": warnings,
        "detailed_steps": detailed_steps
    }
    return result
