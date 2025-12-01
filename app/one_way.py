"""
one_way.py
----------
One-way slab design engine following common IS procedure.
Deflection checks removed (per user request). Depth initial sizing from L/d retained.
"""

import math
from typing import List, Dict

from .constants import (
    DEFAULT_WIDTH,
    MIN_REINFORCEMENT_RATIO,
    DEFAULT_FCK,
    DEFAULT_FY
)
from .units import moment_kNm_to_Nmm
from .helpers import (
    effective_span_clear,
    slab_self_weight,
    total_dead_load,
    factored_load,
    clamp,
    round_up
)
from .reinforcement import recommend_bars

RECOMMENDED_COVER_BY_EXPOSURE = {
    "Mild": 20,
    "Moderate": 30,
    "Severe": 45,
    "Very Severe": 50,
    "Extreme": 75
}


def solve_ast_from_mu(Mu_Nmm: float, d_mm: float, b_mm: float = 1000.0, fck: float = DEFAULT_FCK, fy: float = DEFAULT_FY) -> float:
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


def compute_tau_c_IS(fck: float, ast_mm2_per_m: float, b_mm: float, d_mm: float) -> float:
    if ast_mm2_per_m <= 0 or b_mm <= 0 or d_mm <= 0:
        return 0.0

    p_t = (100.0 * ast_mm2_per_m) / (b_mm * d_mm)  # percentage
    if p_t <= 1e-6:
        p_t = 1e-6

    beta = (0.8 * fck) / (6.89 * p_t)
    factor = (math.sqrt(1.0 + 5.0 * beta) - 1.0) / (6.0 * beta) if beta != 0 else 5.0 / 12.0

    tau_c = 0.85 * math.sqrt(0.8 * fck) * factor
    tau_c_max = 0.63 * math.sqrt(fck)
    if tau_c > tau_c_max:
        tau_c = tau_c_max

    return tau_c


def design_oneway_slab(
    clear_span_m: float,
    live_load_kN_m2: float = 3.0,
    floor_finish_kN_m2: float = 0.5,
    partitions_kN_per_m: float = 0.0,
    strip_width_m: float = DEFAULT_WIDTH / 1000.0,
    support_width_m: float = 0.0,
    L_div_d: float = 20.0,
    cover_mm: float = 20.0,
    bar_dia_mm: int = 10,
    fck: float = DEFAULT_FCK,
    fy: float = DEFAULT_FY,
    exposure: str = "Moderate",
    wall_thickness_mm: float = 115.0
) -> Dict:
    detailed_steps: List[Dict] = []
    warnings: List[str] = []

    detailed_steps.append({
        "title": "Inputs summary",
        "body": (
            f"Clear span Lc = {clear_span_m:.3f} m\n"
            f"Support width = {support_width_m:.3f} m\n"
            f"Live load = {live_load_kN_m2:.3f} kN/m²\n"
            f"Floor finish = {floor_finish_kN_m2:.3f} kN/m²\n"
            f"Partition load (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"Concrete grade fck = {fck} MPa, Steel fy = {fy} MPa\n"
            f"Nominal cover (user) = {cover_mm} mm, Bar dia = {bar_dia_mm} mm\n"
            f"Exposure: {exposure}\n"
            f"Wall thickness = {wall_thickness_mm:.1f} mm\n"
        )
    })

    # Initial depth estimate (L/d guidance used for sizing, not deflection check)
    d_initial_mm = max((clear_span_m * 1000.0) / L_div_d, 100.0)
    detailed_steps.append({
        "title": "Initial effective depth (from L/d)",
        "body": f"Using L/d = {L_div_d}, initial effective depth d_initial = {d_initial_mm:.1f} mm"
    })

    recommended_cover = RECOMMENDED_COVER_BY_EXPOSURE.get(exposure, None)
    detailed_steps.append({
        "title": "Nominal cover (suggested)",
        "body": f"Recommended nominal cover for exposure '{exposure}': {recommended_cover if recommended_cover is not None else 'N/A'} mm (user provided: {cover_mm} mm)"
    })

    # Effective span
    centre_to_centre = clear_span_m + support_width_m
    clear_plus_d = clear_span_m + (d_initial_mm / 1000.0)
    L_eff = min(clear_plus_d, centre_to_centre)
    detailed_steps.append({
        "title": "Effective span",
        "body": (
            f"Centre-to-centre span = {centre_to_centre:.3f} m\n"
            f"Clear span + d_initial = {clear_plus_d:.3f} m\n"
            f"Effective span (min of above) = {L_eff:.3f} m"
        )
    })

    # Final d and D
    d_mm = max((L_eff * 1000.0) / L_div_d, 100.0)
    D_mm = d_mm + cover_mm + (bar_dia_mm / 2.0)
    detailed_steps.append({
        "title": "Final effective & overall depth",
        "body": f"Final effective depth d = {d_mm:.1f} mm; overall depth D = {D_mm:.1f} mm"
    })

    # Loads
    self_wt_kN_per_m = slab_self_weight(D_mm) * strip_width_m
    FF_kN_per_m = floor_finish_kN_m2 * strip_width_m
    LL_kN_per_m = live_load_kN_m2 * strip_width_m
    dead_load_kN_per_m = total_dead_load(self_wt_kN_per_m, FF_kN_per_m, partitions_kN_per_m)
    wu_kN_per_m = factored_load(dead_load_kN_per_m, LL_kN_per_m)

    detailed_steps.append({
        "title": "Loads (per metre strip)",
        "body": (
            f"Self weight = {self_wt_kN_per_m:.3f} kN/m\n"
            f"Floor finish = {FF_kN_per_m:.3f} kN/m\n"
            f"Partitions (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"Dead load (total) = {dead_load_kN_per_m:.3f} kN/m\n"
            f"Factored (ultimate) w_u = 1.5*(DL+LL) = {wu_kN_per_m:.3f} kN/m"
        )
    })

    # Mu & Vu
    Mu_kN_m = wu_kN_per_m * (L_eff ** 2) / 8.0
    Mu_Nmm = moment_kNm_to_Nmm(Mu_kN_m)
    Vu_kN = wu_kN_per_m * L_eff / 2.0
    Vu_N = Vu_kN * 1000.0

    detailed_steps.append({
        "title": "Ultimate bending moment & shear",
        "body": (
            f"Mu = w_u * L^2 / 8 = {Mu_kN_m:.3f} kN·m per metre\n"
            f"Vu (at support) = w_u * L / 2 = {Vu_kN:.3f} kN per metre"
        )
    })

    # Max depth check
    if D_mm > 500.0:
        warnings.append(f"Overall depth D = {D_mm:.1f} mm is large (>500 mm). Consider alternate solution.")
    detailed_steps.append({
        "title": "Maximum depth check",
        "body": f"Overall depth D = {D_mm:.1f} mm (warning if > 500 mm)."
    })

    # Ast
    b_mm = 1000.0
    ast_req = solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=b_mm, fck=fck, fy=fy)
    detailed_steps.append({
        "title": "Required tension steel (Ast) from moment",
        "body": f"Ast required (per metre) = {ast_req:.2f} mm²/m"
    })

    # Shear
    Av_mm2 = b_mm * d_mm
    tau_v = Vu_N / Av_mm2
    tau_c_from_ast = compute_tau_c_IS(fck=fck, ast_mm2_per_m=ast_req, b_mm=b_mm, d_mm=d_mm)

    detailed_steps.append({
        "title": "Shear check (τv vs τc using IS formula)",
        "body": (
            f"Design shear stress τv = Vu/(b*d) = {tau_v:.4f} N/mm²\n"
            f"Computed τc (IS Table 19 formula) using Ast_required: τc = {tau_c_from_ast:.4f} N/mm²\n"
            f"τc_max (Table 20 cap) = {0.63 * math.sqrt(fck):.4f} N/mm²"
        )
    })

    if tau_v > tau_c_from_ast:
        warnings.append(f"Shear stress τv = {tau_v:.4f} N/mm² exceeds τc = {tau_c_from_ast:.4f} N/mm². Provide shear reinforcement or redesign.")
    else:
        detailed_steps.append({"title": "Shear adequacy", "body": "Concrete shear capacity (τc) is adequate; shear reinforcement not required by τv/τc check."})

    # Minimum reinforcement
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm
    if ast_req < ast_min:
        ast_req = ast_min
        detailed_steps.append({"title": "Minimum reinforcement applied", "body": f"Ast increased to minimum reinforcement Ast_min = {ast_min:.2f} mm²/m"})
    else:
        detailed_steps.append({"title": "Minimum reinforcement", "body": f"Ast_min = {ast_min:.2f} mm²/m; Ast_required already >= min."})

    # Cracking (indicator)
    ast_ratio = ast_req / (b_mm * d_mm)
    cracking_msg = f"Ast/(b*d) = {ast_ratio:.6f}"
    if ast_ratio < 0.002:
        cracking_msg += " -> Low steel ratio; serviceability cracking likely; consider increasing Ast."
        warnings.append("Cracking: steel ratio low — serviceability cracking may occur.")
    detailed_steps.append({"title": "Cracking check (indicator)", "body": cracking_msg})

    # Distribution steel
    dist_ast = 0.25 * ast_req
    detailed_steps.append({"title": "Distribution reinforcement recommendation", "body": f"Recommend distribution steel ≈ 25% of main Ast = {dist_ast:.2f} mm²/m"})

    # Bar selection & recommendation
    recommend = recommend_bars(ast_req, preferred_bars=[8, 10, 12, 16, 20, 25], prefer_closer_spacing=False)
    rec = recommend['recommended']
    cand_lines = []
    for c in recommend['candidates']:
        raw = c.get("raw_spacing_mm")
        raw_text = f"{raw:.1f}" if raw is not None else "inf"
        cand_lines.append(f"dia {c['bar_dia_mm']} mm: spacing {c['spacing_mm']} mm (raw {raw_text} mm) -> provided Ast = {c['Ast_provided_mm2_per_m']:.2f} mm2/m; ok={c['ok']}; warnings={c['warnings']}")

    detailed_steps.append({
        "title": "Bar selection candidates (ranked)",
        "body": "Top recommendation:\n" + f"dia {rec['bar_dia_mm']} mm, spacing {rec['spacing_mm']} mm, Ast_prov {rec['Ast_provided_mm2_per_m']:.2f} mm2/m\n\nAll candidates:\n" + "\n".join(cand_lines)
    })

    bar_dia_sel = rec.get("bar_dia_mm")
    spacing_mm = rec.get("spacing_mm")
    ast_provided = rec.get("Ast_provided_mm2_per_m")
    if not rec.get("ok", True):
        for w in rec.get("warnings", []):
            warnings.append(f"Bar recommendation: {w}")

    result = {
        "slab_type": "One-way (IS 456 procedure)",
        "clear_span_m": round(clear_span_m, 3),
        "effective_span_m": round(L_eff, 3),
        "cover_mm_user": cover_mm,
        "recommended_cover_mm": recommended_cover,
        "cover_override_used": False,
        "wall_thickness_mm": round(wall_thickness_mm, 1),
        "d_mm": round(d_mm, 1),
        "D_mm": round(D_mm, 1),
        "dead_load_kN_per_m": round(dead_load_kN_per_m, 3),
        "wu_kN_per_m": round(wu_kN_per_m, 3),
        "Mu_kN_m_per_m": round(Mu_kN_m, 3),
        "Vu_kN_per_m": round(Vu_kN, 3),
        "Ast_required_mm2_per_m": round(ast_req, 2),
        "Ast_provided_mm2_per_m": round(ast_provided, 2) if ast_provided is not None else None,
        "bar_dia_mm": int(bar_dia_sel) if bar_dia_sel is not None else None,
        "spacing_mm": int(spacing_mm) if spacing_mm is not None else None,
        "tau_v_N_per_mm2": round(tau_v, 4),
        "tau_c_used_N_per_mm2": round(tau_c_from_ast, 4),
        "fck": fck,
        "fy": fy,
        "exposure_condition": exposure,
        "warnings": warnings,
        "detailed_steps": detailed_steps
    }

    return result
