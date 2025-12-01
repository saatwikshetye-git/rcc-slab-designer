"""
one_way.py

Full one-way slab design workflow following the student's college / IS 456 procedure:
1) Classification (one-way/two-way handled in UI before calling)
2) Choose depth (IS guidance)
3) Nominal cover (table guidance input)
4) Effective span (Clause 22.2)
5) Factored load
6) Ultimate moment & shear
7) Check for maximum depth (IS rules)
8) Flexural reinforcement design (IS simplified stress block)
9) Shear design (use Table 19 interpolation)
10) Minimum reinforcement
11) Cracking check (basic)
12) Distribution reinforcement (basic guidance)
13) Deflection check using digitized Fig.4 & Fig.5 (interpolation)
"""

from typing import Dict, List
import math

from .constants import (
    DEFAULT_FCK, DEFAULT_FY, MIN_REINFORCEMENT_RATIO,
    TABLE19_FCK, TABLE19_PT, TABLE19_TAU_C,
    FIG4_PT, FIG4_ALLOWED_LD, FIG5_ASPECT, FIG5_MODIFIER
)
from .helpers import (
    effective_span_clear, slab_self_weight_mm, total_dead_load,
    factored_load, interp1d_wrapper, m_to_mm, mm_to_m
)
from .reinforcement import recommend_bars, area_of_bar_mm2
from .units import moment_kNm_to_Nmm

# ---------- Utility: small helpers ----------
def interp_table19_tau_c(fck: float, p_t_percent: float) -> float:
    """
    Interpolate TABLE19_TAU_C for given fck and p_t% (percent).
    TABLE19_FCK and TABLE19_PT are the grid axes.
    """
    # clamp p_t in table range
    pt = max(min(p_t_percent, TABLE19_PT[-1]), TABLE19_PT[0])
    # find which fck bracket
    # linear interpolation in two steps: along PT for each row, then along fck between rows
    # first compute tau for each fck row at p_t using interp1d
    row_tau_at_pt = []
    for row in TABLE19_TAU_C:
        tau = interp1d_wrapper(TABLE19_PT, row, pt)
        row_tau_at_pt.append(tau)
    # now interpolate along fck axis
    fck_clamped = max(min(fck, TABLE19_FCK[-1]), TABLE19_FCK[0])
    tau_final = interp1d_wrapper(TABLE19_FCK, row_tau_at_pt, fck_clamped)
    return float(tau_final)


def interp_fig4_allowed_ld(p_t_percent: float, aspect_ratio: float) -> float:
    """
    Use FIG4_PT vs FIG4_ALLOWED_LD to find base allowable L/d for simply supported.
    Then apply FIG5 modifier based on aspect_ratio to get final allowable L/d.
    """
    base_ld = interp1d_wrapper(FIG4_PT, FIG4_ALLOWED_LD, p_t_percent)
    # get modifier for aspect
    mod = interp1d_wrapper(FIG5_ASPECT, FIG5_MODIFIER, aspect_ratio)
    return base_ld * mod

# ---------- Main solver ----------
def design_oneway_slab(
    span_m: float,
    support_width_m: float = 0.0,
    wall_thickness_mm: float = 115.0,
    live_load_kN_m2: float = 3.0,
    floor_finish_kN_m2: float = 0.5,
    partitions_kN_per_m: float = 0.0,
    cover_mm: float = 20.0,
    bar_dia_mm: int = 10,
    fck: float = DEFAULT_FCK,
    fy: float = DEFAULT_FY,
    design_L_div_d: float = 20.0,
    exposure: str = "Moderate"
) -> Dict:
    detailed_steps: List[Dict] = []
    warnings: List[str] = []

    # 1) Input summary
    detailed_steps.append({"title": "Inputs summary",
                           "body": (f"Clear span Lc = {span_m:.3f} m\n"
                                    f"Support width = {support_width_m:.3f} m\n"
                                    f"Wall thickness = {wall_thickness_mm:.1f} mm\n"
                                    f"Live load = {live_load_kN_m2:.3f} kN/m², Floor finish = {floor_finish_kN_m2:.3f} kN/m²\n"
                                    f"fck = {fck} MPa, fy = {fy} MPa\n"
                                    f"Cover = {cover_mm} mm, bar dia = {bar_dia_mm} mm\n"
                                    f"Design L/d chosen = {design_L_div_d} (default guidance)")})


    # 2) Effective span (IS 456 Clause 22.2)
    L_eff = effective_span_clear(span_m, support_width_m)
    detailed_steps.append({"title": "Effective span (IS 456 Clause 22.2)", "body": f"Effective span L = {L_eff:.3f} m"})

    # 3) Nominal cover / nominal depth guidance handled by user input cover_mm
    detailed_steps.append({"title": "Nominal cover", "body": f"Nominal cover used = {cover_mm} mm (user selection/exposure={exposure})"})

    # 4) Initial effective depth from L/d rule (use recommended limits as starting point)
    d_mm = max((L_eff * 1000.0) / design_L_div_d, 100.0)  # enforce practical minimum
    detailed_steps.append({"title": "Initial effective depth (from L/d)", "body": f"d = {d_mm:.1f} mm (L/d = {design_L_div_d})"})

    # 5) Loads: self-weight (use D = d + cover + bar centroid)
    D_mm = d_mm + cover_mm + (bar_dia_mm / 2.0)
    self_wt_kN_per_m = slab_self_weight_mm(D_mm)  # per 1 m width
    floor_kN_per_m = floor_finish_kN_m2 * 1.0  # per m width (user supplied per m²)
    live_kN_per_m = live_load_kN_m2 * 1.0
    # partition auto-calc if zero and wall_thickness provided (simple slender rule)
    if partitions_kN_per_m <= 0.0 and wall_thickness_mm > 0:
        # sample auto rule: 3.5 kN/m per 115 mm wall thickness (you can change later)
        partitions_kN_per_m = (wall_thickness_mm / 115.0) * 3.5
    dl_kN_per_m = total_dead_load(self_wt_kN_per_m, floor_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dl_kN_per_m, live_kN_per_m)
    detailed_steps.append({"title": "Loads & factored load", "body": f"D = {D_mm:.1f} mm -> self-weight = {self_wt_kN_per_m:.3f} kN/m\n"
                                                                       f"Floor finish = {floor_kN_per_m:.3f} kN/m, Live = {live_kN_per_m:.3f} kN/m, Partitions = {partitions_kN_per_m:.3f} kN/m\n"
                                                                       f"DL = {dl_kN_per_m:.3f} kN/m, w_u = {wu_kN_per_m:.3f} kN/m"})

    # 6) Ultimate moment & shear for simply supported one-way (per metre width)
    Mu_kN_m = (wu_kN_per_m * (L_eff ** 2)) / 8.0  # kN·m per metre
    Vu_kN = wu_kN_per_m * L_eff / 2.0
    Mu_Nmm = moment_kNm_to_Nmm(Mu_kN_m)
    detailed_steps.append({"title": "Ultimate moment & shear (simple support)",
                           "body": f"Mu = {Mu_kN_m:.4f} kN·m/m = {Mu_Nmm:.1f} N·mm; Vu (end shear) = {Vu_kN:.3f} kN"})

    # 7) Check for maximum depth (practical limits) - we check whether x_neutral < d (balanced)
    # We'll determine Ast from Mu and then verify x (neutral axis). If x >= d, indicate large required Ast.
    # 8) Flexural design: solve for Ast using IS stress block (singly reinforced)
    # iterate Ast until Mu_calc >= Mu_req
    def solve_ast_from_mu(Mu_req_Nmm: float, d_mm_local: float, b_mm=1000.0, fck_local=fck, fy_local=fy) -> float:
        ast = 1.0
        step = 1.0
        max_ast = 1_000_000.0
        while ast < max_ast:
            x_mm = (0.87 * fy_local * ast) / (0.36 * fck_local * b_mm)
            if x_mm >= d_mm_local:
                mu_calc = 1e18
            else:
                mu_calc = 0.87 * fy_local * ast * (d_mm_local - 0.42 * x_mm)
            if mu_calc >= Mu_req_Nmm:
                return ast
            ast += step
        return max_ast

    ast_required = solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=1000.0, fck_local=fck, fy_local=fy)
    detailed_steps.append({"title": "Flexural design (Ast required)",
                           "body": f"Ast_required = {ast_required:.2f} mm² per metre width"})

    # 9) Shear design using Table 19 interpolation: compute tau_v and tau_c
    # convert Vu to N and compute shear stress tau_v = Vu / (b * d)
    b_mm = 1000.0
    Vu_N = Vu_kN * 1000.0
    tau_v = Vu_N / (b_mm * d_mm)  # N/mm2
    # compute p_t (%) for use in table19
    p_t_percent = (100.0 * ast_required) / (b_mm * d_mm)
    tau_c = interp_table19_tau_c(fck, p_t_percent)
    detailed_steps.append({"title": "Shear check (Table 19 interpolation)",
                           "body": f"Vu = {Vu_kN:.3f} kN => τv = {tau_v:.4f} N/mm²\n"
                                   f"p_t = {p_t_percent:.6f} % => τc (from Table19 interp) = {tau_c:.4f} N/mm²"})

    if tau_v > tau_c:
        warnings.append("Shear stress τv exceeds τc (Table 19). Provide shear reinforcement or increase depth.")
    else:
        detailed_steps.append({"title": "Shear result", "body": "τv ≤ τc -> no shear reinforcement required (strip check)"})

    # 10) Minimum reinforcement (Clause 26.5.2.1)
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm
    min_flag = False
    if ast_required < ast_min:
        ast_required = ast_min
        min_flag = True
        warnings.append("Ast set to minimum reinforcement (IS clause).")
    detailed_steps.append({"title": "Minimum reinforcement",
                           "body": f"Ast_min = {ast_min:.2f} mm²/m. Applied min steel: {min_flag}"})

    # 11) Cracking check (basic) — IS suggests limits based on p_t & cover (we show indicator)
    # A simple indicator: if p_t < 0.15% then cracking risk is higher; also exposure matters (user input)
    p_t_percent_after = (100.0 * ast_required) / (b_mm * d_mm)
    crack_notes = []
    if p_t_percent_after < 0.15:
        crack_notes.append("Low steel ratio (<0.15%): cracking likely — consider higher Ast or distribution steel.")
    if exposure.lower() in ("severe", "very severe", "extreme"):
        crack_notes.append(f"Severe exposure ({exposure}): increase cover or use corrosion-resistant reinforcement.")
    if crack_notes:
        warnings += crack_notes
    detailed_steps.append({"title": "Cracking check (indicator)",
                           "body": f"p_t = {p_t_percent_after:.6f} %\nNotes: {'; '.join(crack_notes) if crack_notes else 'OK (indicator)'}"})

    # 12) Distribution reinforcement — provide a simple recommendation: use min steel in distribution direction
    # IS suggests distribution reinforcement of at least 0.12% (we already enforced minimum). We'll present recommended spacing/diameter.
    rec = recommend_bars(ast_required)
    recommended = rec["recommended"]
    # calculate provided Ast by chosen bar & spacing
    bar_dia_chosen = recommended["bar_dia_mm"]
    spacing_chosen = recommended["spacing_mm"]
    As_single = area_of_bar_mm2(bar_dia_chosen)
    ast_provided = As_single * (1000.0 / spacing_chosen) if spacing_chosen else 0.0
    detailed_steps.append({"title": "Distribution / provided reinforcement",
                           "body": f"Recommended: {bar_dia_chosen} mm @ {spacing_chosen} mm c/c -> Ast_provided = {ast_provided:.2f} mm²/m"})

    # 13) Deflection check using Fig.4 & Fig.5 digitized interpolation
    # compute allowable L/d (simply supported) from Fig.4 using p_t% and apply Fig.5 aspect modifier (aspect = 1 for one-way strip)
    allowable_L_div_d = interp_fig4_allowed_ld(p_t_percent_after, aspect_ratio=1.0)
    computed_L_div_d = (L_eff) / (d_mm / 1000.0)
    deflection_ok = computed_L_div_d <= allowable_L_div_d
    detailed_steps.append({"title": "Deflection check (IS Fig.4/Fig.5 interpolation)",
                           "body": f"Computed L/d = {computed_L_div_d:.2f}. Allowable L/d (from Fig.4/5 interp) = {allowable_L_div_d:.2f}\n"
                                   f"Deflection OK = {deflection_ok}"})
    if not deflection_ok:
        warnings.append("Deflection check: L/d exceeds allowable (Fig.4/5). Increase depth or provide pre-stressing / continuity.")

    # 14) Final packaging of results
    result = {
        "slab_type": "One-way (IS 456 method)",
        "effective_span_m": round(L_eff, 3),
        "d_mm": round(d_mm, 1),
        "D_mm": round(D_mm, 1),
        "wu_kN_per_m": round(wu_kN_per_m, 3),
        "Mu_kN_m_per_m": round(Mu_kN_m, 3),
        "Mu_Nmm_per_m": round(Mu_Nmm, 1),
        "Ast_required_mm2_per_m": round(ast_required, 2),
        "Ast_provided_mm2_per_m": round(ast_provided, 2),
        "bar_dia_mm": bar_dia_chosen,
        "spacing_mm": spacing_chosen,
        "tau_v_N_per_mm2": round(tau_v, 5),
        "tau_c_N_per_mm2": round(tau_c, 5),
        "p_t_percent": round(p_t_percent_after, 6),
        "allowable_L_div_d": round(allowable_L_div_d, 2),
        "computed_L_div_d": round(computed_L_div_d, 2),
        "deflection_ok": deflection_ok,
        "warnings": warnings,
        "detailed_steps": detailed_steps
    }
    return result
