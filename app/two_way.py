"""
two_way.py
----------
Two-way slab design following your college procedure (IS 456).

Inputs:
  - Lx_m, Ly_m (metres)
  - wall_thickness_mm (for partition load estimate)
  - live_load_kN_m2, floor_finish_kN_m2
  - fck (MPa), fy (MPa)
  - cover_mm, bar diameters for X & Y (optional)
  - strip_width_m (defaults to 1m)

Procedure implemented (per your request):
1. slab thickness (initial from L/d guidance)
2. effective span (IS 456 cl.22.2) with 1-step iteration (d -> L_eff -> d)
3. factored loads (1.5*(DL+LL))
4. ultimate moments using Table 27 alpha coefficients (interpolated)
5. maximum (check both directions)
6. check for maximum practical depth (warning)
7. reinforcement in slab (Ast) using IS stress block (solve_ast_from_mu)
8. minimum reinforcement (IS clause)
9. repeat for short & long span
10. cracking checks (indicator)
11. shear checks: τv vs τc (compute_tau_c_IS used)
12. deflection: **NOT APPLIED** here because IS deflection modifiers (Fig.4/Fig.5) are graphical.
    The code flags that Fig.4/Fig.5 interpolation data are required and returns the information needed.
    If you want, I will digitize Fig.4/Fig.5 and add the interpolation next (no placeholders).

Notes:
- Table 27 α coefficients are taken from constants.TABLE27_* arrays and interpolated by constants.get_table27_alphas().
- compute_tau_c_IS and solve_ast_from_mu are imported from one_way.py (they follow IS formulations).
"""

import math
from typing import Dict, List

from .constants import (
    get_table27_alphas,
    DEFAULT_WIDTH,
    DEFAULT_FCK,
    DEFAULT_FY,
    MIN_REINFORCEMENT_RATIO,
    MAX_BAR_SPACING,
    TABLE27_LY_LX
)
from .one_way import solve_ast_from_mu, compute_tau_c_IS
from .helpers import slab_self_weight, total_dead_load, factored_load
from .reinforcement import recommend_bars
from .units import moment_kNm_to_Nmm

# Default candidate bars for selection
DEFAULT_BARS = [8, 10, 12, 16, 20, 25]


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
    fck: float = DEFAULT_FCK,
    fy: float = DEFAULT_FY,
    L_div_d: float = 20.0,
    exposure: str = "Moderate",
    table27_source_note: str = "IS 456 Table 27 (Annex D)"
) -> Dict:
    """
    Two-way slab design (per metre strip). Returns result dict with detailed steps.
    """
    detailed_steps: List[Dict] = []
    warnings: List[str] = []

    # ---------------------
    # Step 0: Inputs summary
    # ---------------------
    detailed_steps.append({
        "title": "Inputs summary",
        "body": (
            f"Lx = {Lx_m:.3f} m (short or long depending on ratio)\n"
            f"Ly = {Ly_m:.3f} m\n"
            f"Wall thickness = {wall_thickness_mm:.1f} mm\n"
            f"Live load = {live_load_kN_m2:.3f} kN/m²\n"
            f"Floor finish = {floor_finish_kN_m2:.3f} kN/m²\n"
            f"Partition load (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"Concrete grade fck = {fck} MPa, Steel fy = {fy} MPa\n"
            f"Cover = {cover_mm} mm, Bar dia X = {bar_dia_x_mm} mm, Bar dia Y = {bar_dia_y_mm} mm\n"
            f"Table source: {table27_source_note}\n"
        )
    })

    # ---------------------
    # Step 1: initial thickness (effective depth via L/d)
    # We will compute d based on short and long spans separately using L_div_d (conservative).
    # ---------------------
    # We'll perform a one-step iteration for each direction where necessary.
    # For two-way, Table 27 assumes ly >= lx so handle mapping.
    if Ly_m >= Lx_m:
        L_short = Lx_m
        L_long = Ly_m
        short_name = "Lx"
        long_name = "Ly"
    else:
        L_short = Ly_m
        L_long = Lx_m
        short_name = "Ly"
        long_name = "Lx"

    detailed_steps.append({
        "title": "Span classification",
        "body": (
            f"Short span = {L_short:.3f} m ({short_name})\n"
            f"Long span  = {L_long:.3f} m ({long_name})\n"
            f"Aspect ratio ly/lx = {L_long / L_short:.3f}"
        )
    })

    # We will compute initial d for short and long using L_div_d
    d_short_initial_mm = max((L_short * 1000.0) / L_div_d, 100.0)
    d_long_initial_mm = max((L_long * 1000.0) / L_div_d, 100.0)

    detailed_steps.append({
        "title": "Initial effective depths",
        "body": f"d_short_initial = {d_short_initial_mm:.1f} mm; d_long_initial = {d_long_initial_mm:.1f} mm (from L/d = {L_div_d})"
    })

    # ---------------------
    # Step 2: effective span (IS 456 cl.22.2) for both directions
    # Use 1 step iteration: compute centre-to-centre and clear+d then choose min, recompute d
    # ---------------------
    # Support width is ambiguous for two-way (depends on support), use same support width = wall thickness? No.
    # Here we do effective span based on clear span + assumed support width 0 (user provides Lx/Ly as clear spans).
    # If user has support width info, it should be passed separately; currently assume supports small and use clear + d logic.
    centre_x = Lx_m  # treating Lx_m as centre-to-centre if support widths not provided separately
    centre_y = Ly_m

    # compute clear + d candidates and pick min for both
    clear_plus_d_short = L_short + (d_short_initial_mm / 1000.0)
    centre_to_centre_short = L_short  # if support width unknown, centre-to-centre approximated by L_short
    L_eff_short = min(clear_plus_d_short, centre_to_centre_short)

    clear_plus_d_long = L_long + (d_long_initial_mm / 1000.0)
    centre_to_centre_long = L_long
    L_eff_long = min(clear_plus_d_long, centre_to_centre_long)

    # Recompute d using L_eff (one iteration)
    d_short_mm = max((L_eff_short * 1000.0) / L_div_d, 100.0)
    d_long_mm = max((L_eff_long * 1000.0) / L_div_d, 100.0)

    D_short_mm = d_short_mm + cover_mm + (bar_dia_x_mm / 2.0)  # nominal overall thickness for short-direction design (use X bars centroid)
    D_long_mm = d_long_mm + cover_mm + (bar_dia_y_mm / 2.0)

    detailed_steps.append({
        "title": "Effective span & final depths (one-step iteration)",
        "body": (
            f"Short-direction: L_eff_short = {L_eff_short:.3f} m, computed d_short = {d_short_mm:.1f} mm, D_short = {D_short_mm:.1f} mm\n"
            f"Long-direction:  L_eff_long  = {L_eff_long:.3f} m, computed d_long  = {d_long_mm:.1f} mm, D_long  = {D_long_mm:.1f} mm"
        )
    })

    # ---------------------
    # Step 3: factored load
    # ---------------------
    # Estimate self weight using assumed D (conservative: use larger of D_short and D_long)
    assumed_D_mm = max(D_short_mm, D_long_mm)
    self_wt_kN_per_m = slab_self_weight(assumed_D_mm) * strip_width_m
    FF_kN_per_m = floor_finish_kN_m2 * strip_width_m
    LL_kN_per_m = live_load_kN_m2 * strip_width_m

    # partitions: if provided use it, else estimate from wall_thickness_mm
    if partitions_kN_per_m <= 0.0 and wall_thickness_mm > 0:
        # default conservative estimate (brick masonry density & 2.7m height)
        # Use common approximations: 115 mm ~ 3.5 kN/m; scale linearly
        partitions_kN_per_m = (wall_thickness_mm / 115.0) * 3.5

    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, FF_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, LL_kN_per_m)

    detailed_steps.append({
        "title": "Factored loads",
        "body": (
            f"Assumed overall depth (for self-weight) = {assumed_D_mm:.1f} mm -> self weight = {self_wt_kN_per_m:.3f} kN/m\n"
            f"Floor finish per m = {FF_kN_per_m:.3f} kN/m, Live per m = {LL_kN_per_m:.3f} kN/m\n"
            f"Partitions (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"Total dead load = {dead_load_kN_per_m:.3f} kN/m\n"
            f"Ultimate load w_u = 1.5*(DL+LL) = {wu_kN_per_m:.3f} kN/m"
        )
    })

    # ---------------------
    # Step 4: factored moments using Table 27
    # alpha_x multiplies w * (short span)^2
    # alpha_y multiplies w * (long span)^2
    # Use get_table27_alphas(ratio) from constants
    # ---------------------
    ly_lx_ratio = L_long / L_short
    alpha_x, alpha_y = get_table27_alphas(ly_lx_ratio)  # alpha_x corresponds to short-direction moment coefficient

    # Moments per metre (kN·m/m)
    Mx_kN_m = alpha_x * wu_kN_per_m * (L_short ** 2)
    My_kN_m = alpha_y * wu_kN_per_m * (L_long ** 2)

    Mx_Nmm = moment_kNm_to_Nmm(Mx_kN_m)
    My_Nmm = moment_kNm_to_Nmm(My_kN_m)

    detailed_steps.append({
        "title": "Moments from Table 27 (interpolated)",
        "body": (
            f"Aspect ratio (ly/lx) = {ly_lx_ratio:.4f}\n"
            f"Interpolated alpha_x = {alpha_x:.6f}, alpha_y = {alpha_y:.6f}\n"
            f"Mx = alpha_x * w * L_short^2 = {Mx_kN_m:.4f} kN·m/m\n"
            f"My = alpha_y * w * L_long^2  = {My_kN_m:.4f} kN·m/m"
        )
    })

    # ---------------------
    # Step 5: maximum factored moment and checking for depth
    # Solve for Ast required in short and long directions using solve_ast_from_mu
    # ---------------------
    b_mm = 1000.0  # per metre strip

    ast_short_req = solve_ast_from_mu(Mx_Nmm, d_short_mm, b_mm=b_mm, fck=fck, fy=fy)
    ast_long_req = solve_ast_from_mu(My_Nmm, d_long_mm, b_mm=b_mm, fck=fck, fy=fy)

    detailed_steps.append({
        "title": "Required tension steel (Ast) from moments",
        "body": (
            f"Ast_short_required (per m) = {ast_short_req:.2f} mm²/m (for Mx = {Mx_kN_m:.4f} kN·m/m)\n"
            f"Ast_long_required  (per m) = {ast_long_req:.2f} mm²/m (for My = {My_kN_m:.4f} kN·m/m)"
        )
    })

    # ---------------------
    # Step 6: check for maximum practical depth (warning)
    # ---------------------
    max_D_allowed = 500.0  # practical limit
    if D_short_mm > max_D_allowed:
        warnings.append(f"Short-direction overall depth D_short = {D_short_mm:.1f} mm exceeds practical limit {max_D_allowed} mm.")
    if D_long_mm > max_D_allowed:
        warnings.append(f"Long-direction overall depth D_long = {D_long_mm:.1f} mm exceeds practical limit {max_D_allowed} mm.")

    detailed_steps.append({
        "title": "Maximum depth check",
        "body": f"D_short = {D_short_mm:.1f} mm; D_long = {D_long_mm:.1f} mm; practical limit = {max_D_allowed} mm"
    })

    # ---------------------
    # Step 7 & 8: reinforcement & minimum reinforcement (IS clause)
    # ---------------------
    ast_short_min = MIN_REINFORCEMENT_RATIO * b_mm * d_short_mm
    ast_long_min = MIN_REINFORCEMENT_RATIO * b_mm * d_long_mm

    short_min_flag = False
    long_min_flag = False

    if ast_short_req < ast_short_min:
        ast_short_req = ast_short_min
        short_min_flag = True
    if ast_long_req < ast_long_min:
        ast_long_req = ast_long_min
        long_min_flag = True

    detailed_steps.append({
        "title": "Minimum reinforcement check",
        "body": (
            f"Ast_short_min = {ast_short_min:.2f} mm²/m; Ast_long_min = {ast_long_min:.2f} mm²/m\n"
            f"Applied min flags: short_min={short_min_flag}, long_min={long_min_flag}"
        )
    })

    # ---------------------
    # Step 9: bar selection & spacing for provided bar diameters (map to X/Y directions)
    # Use recommended bars helper for each direction
    # ---------------------
    # For mapping: alpha_x returned is for short-direction (Mx). If Ly >= Lx then short=Lx maps to X-input.
    if Ly_m >= Lx_m:
        # X direction corresponds to short (Lx) and uses bar_dia_x_mm
        ast_x_req = ast_short_req
        ast_y_req = ast_long_req
        d_x_mm = d_short_mm
        d_y_mm = d_long_mm
        bar_x_dia = bar_dia_x_mm
        bar_y_dia = bar_dia_y_mm
    else:
        # swap mapping
        ast_x_req = ast_long_req
        ast_y_req = ast_short_req
        d_x_mm = d_long_mm
        d_y_mm = d_short_mm
        bar_x_dia = bar_dia_x_mm  # user still provided bar_dia_x,bar_dia_y; we keep same variable names
        bar_y_dia = bar_dia_y_mm

    # Candidate recommendations
    rec_x = recommend_bars(ast_x_req, preferred_bars=DEFAULT_BARS, prefer_closer_spacing=False)
    rec_y = recommend_bars(ast_y_req, preferred_bars=DEFAULT_BARS, prefer_closer_spacing=False)

    # chosen candidates
    chosen_x = rec_x["recommended"]
    chosen_y = rec_y["recommended"]

    # compute provided Ast actual
    ast_x_prov = chosen_x["Ast_provided_mm2_per_m"]
    ast_y_prov = chosen_y["Ast_provided_mm2_per_m"]

    detailed_steps.append({
        "title": "Bar selection (recommended)",
        "body": (
            f"X-direction: recommended dia {chosen_x['bar_dia_mm']} mm, spacing {chosen_x['spacing_mm']} mm -> Ast_prov = {ast_x_prov:.2f} mm²/m\n"
            f"Y-direction: recommended dia {chosen_y['bar_dia_mm']} mm, spacing {chosen_y['spacing_mm']} mm -> Ast_prov = {ast_y_prov:.2f} mm²/m"
        )
    })

    # ---------------------
    # Step 10: cracking check (indicator)
    # ---------------------
    ast_ratio_x = ast_x_req / (b_mm * d_x_mm)
    ast_ratio_y = ast_y_req / (b_mm * d_y_mm)

    crack_msgs = []
    if ast_ratio_x < 0.002:
        crack_msgs.append("X-direction: low steel ratio; cracking likely.")
    if ast_ratio_y < 0.002:
        crack_msgs.append("Y-direction: low steel ratio; cracking likely.")

    detailed_steps.append({
        "title": "Cracking check (indicators)",
        "body": f"Ast/bd: X = {ast_ratio_x:.6f}, Y = {ast_ratio_y:.6f}. Notes: {'; '.join(crack_msgs) if crack_msgs else 'OK'}"
    })
    if crack_msgs:
        warnings.extend(crack_msgs)

    # ---------------------
    # Step 11: shear checks for both directions (τv vs τc)
    # τv = Vu/(b*d) where Vu depends on panel moments and load distribution.
    # For two-way slabs, shear distribution is complex; we apply conservative check using Vu = w*L/2 per metre for short & long spans.
    # This is conservative and standard for checking slab shear per metre strip.
    # ---------------------
    Vu_short_kN = wu_kN_per_m * L_short / 2.0
    Vu_long_kN = wu_kN_per_m * L_long / 2.0
    Vu_short_N = Vu_short_kN * 1000.0
    Vu_long_N = Vu_long_kN * 1000.0

    tau_v_short = Vu_short_N / (b_mm * d_short_mm)
    tau_v_long = Vu_long_N / (b_mm * d_long_mm)

    # compute tau_c using Ast_required (conservative) for each direction
    tau_c_short = compute_tau_c_IS(fck=fck, ast_mm2_per_m=ast_short_req, b_mm=b_mm, d_mm=d_short_mm)
    tau_c_long = compute_tau_c_IS(fck=fck, ast_mm2_per_m=ast_long_req, b_mm=b_mm, d_mm=d_long_mm)

    detailed_steps.append({
        "title": "Shear checks",
        "body": (
            f"Short-direction: Vu = {Vu_short_kN:.3f} kN/m -> τv = {tau_v_short:.4f} N/mm²; τc = {tau_c_short:.4f} N/mm²\n"
            f"Long-direction:  Vu = {Vu_long_kN:.3f} kN/m -> τv = {tau_v_long:.4f} N/mm²; τc = {tau_c_long:.4f} N/mm²"
        )
    })

    if tau_v_short > tau_c_short:
        warnings.append(f"Short-direction shear τv = {tau_v_short:.4f} N/mm² exceeds τc = {tau_c_short:.4f} N/mm² -> provide shear reinforcement or redesign.")
    if tau_v_long > tau_c_long:
        warnings.append(f"Long-direction shear τv = {tau_v_long:.4f} N/mm² exceeds τc = {tau_c_long:.4f} N/mm² -> provide shear reinforcement or redesign.")

    # ---------------------
    # Step 12: Deflection check (IS Fig.4/Fig.5 modifiers REQUIRED)
    # We WILL NOT use basic L/d here (per your instruction). The correct IS procedure requires modification factors
    # from Fig.4 and Fig.5 (Kt, Kc) and computing allowable L/d_allowable = basic_ratio * Kt * Kc etc.
    # Those curves are graphical in IS 456; we do NOT have digitized points in this run unless you ask me to digitize them.
    # Therefore we **flag** deflection as "REQUIRES IS FIG4/FIG5 DATA" and include the numeric values needed for applying them.
    # ---------------------
    # Provide the data needed for deflection check:
    # - percentage steel p_tension (for each direction) = 100 * Ast / (b*d)
    p_t_x = (100.0 * ast_x_req) / (b_mm * d_x_mm)
    p_t_y = (100.0 * ast_y_req) / (b_mm * d_y_mm)

    detailed_steps.append({
        "title": "Deflection check (requires IS Fig.4/Fig.5 interpolation)",
        "body": (
            "IS 456 Fig.4 and Fig.5 modifiers are required to compute modification factors for tension/compression steel.\n"
            "This code does not assume L/d basic rule for two-way deflection. To finish this step you must provide digitized\n"
            "Fig.4 and Fig.5 data or ask me to digitize and embed them. Data required:\n"
            f"- p_tension X-direction (percent) = {p_t_x:.6f}\n"
            f"- p_tension Y-direction (percent) = {p_t_y:.6f}\n"
            "Once Fig.4 & Fig.5 curves are available, allowable L/d will be computed and compared to actual."
        )
    })

    warnings.append("Deflection check not completed: IS Fig.4/Fig.5 modifiers required. Ask me to digitize and embed them to finish deflection check.")

    # ---------------------
    # Package results (map back to user X/Y naming)
    # ---------------------
    if Ly_m >= Lx_m:
        # short->X, long->Y mapping
        result = {
            "slab_type": "Two-way (Table 27 method)",
            "ly_lx_ratio": round(ly_lx_ratio, 4),
            "wu_kN_per_m": round(wu_kN_per_m, 4),
            "alpha_short": round(alpha_x, 6),
            "alpha_long": round(alpha_y, 6),
            "L_short_m": round(L_short, 3),
            "L_long_m": round(L_long, 3),
            "Mx_kN_m_per_m": round(Mx_kN_m, 4),
            "My_kN_m_per_m": round(My_kN_m, 4),
            "d_short_mm": round(d_short_mm, 1),
            "d_long_mm": round(d_long_mm, 1),
            "Ast_short_req_mm2_per_m": round(ast_short_req, 2),
            "Ast_short_prov_mm2_per_m": round(ast_x_prov, 2),
            "spacing_short_mm": int(chosen_x["spacing_mm"]),
            "Ast_long_req_mm2_per_m": round(ast_long_req, 2),
            "Ast_long_prov_mm2_per_m": round(ast_y_prov, 2),
            "spacing_long_mm": int(chosen_y["spacing_mm"]),
            "tau_v_short_N_per_mm2": round(tau_v_short, 4),
            "tau_c_short_N_per_mm2": round(tau_c_short, 4),
            "tau_v_long_N_per_mm2": round(tau_v_long, 4),
            "tau_c_long_N_per_mm2": round(tau_c_long, 4),
            "p_t_x_percent": round(p_t_x, 6),
            "p_t_y_percent": round(p_t_y, 6),
            "deflection_check": "REQUIRES_FIG4_FIG5_DATA",
            "fck": fck,
            "fy": fy,
            "cover_mm": cover_mm,
            "warnings": warnings,
            "detailed_steps": detailed_steps
        }
    else:
        # mapping swapped (Lx was longer)
        result = {
            "slab_type": "Two-way (Table 27 method)",
            "ly_lx_ratio": round(ly_lx_ratio, 4),
            "wu_kN_per_m": round(wu_kN_per_m, 4),
            "alpha_short": round(alpha_x, 6),
            "alpha_long": round(alpha_y, 6),
            "L_short_m": round(L_short, 3),
            "L_long_m": round(L_long, 3),
            "Mx_kN_m_per_m": round(Mx_kN_m, 4),
            "My_kN_m_per_m": round(My_kN_m, 4),
            "d_short_mm": round(d_short_mm, 1),
            "d_long_mm": round(d_long_mm, 1),
            "Ast_short_req_mm2_per_m": round(ast_short_req, 2),
            "Ast_short_prov_mm2_per_m": round(ast_x_prov, 2),
            "spacing_short_mm": int(chosen_x["spacing_mm"]),
            "Ast_long_req_mm2_per_m": round(ast_long_req, 2),
            "Ast_long_prov_mm2_per_m": round(ast_y_prov, 2),
            "spacing_long_mm": int(chosen_y["spacing_mm"]),
            "tau_v_short_N_per_mm2": round(tau_v_short, 4),
            "tau_c_short_N_per_mm2": round(tau_c_short, 4),
            "tau_v_long_N_per_mm2": round(tau_v_long, 4),
            "tau_c_long_N_per_mm2": round(tau_c_long, 4),
            "p_t_x_percent": round(p_t_x, 6),
            "p_t_y_percent": round(p_t_y, 6),
            "deflection_check": "REQUIRES_FIG4_FIG5_DATA",
            "fck": fck,
            "fy": fy,
            "cover_mm": cover_mm,
            "warnings": warnings,
            "detailed_steps": detailed_steps
        }

    return result
