"""
one_way.py
----------
One-way slab design engine following the college procedure provided:
1) check one-way vs two-way by ly/lx
2) depth of slab (initial and final)
3) nominal cover (based on exposure)
4) effective span
5) factored load
6) ultimate moment and shear
7) check for maximum depth (practical limits)
8) reinforcement area (Ast)
9) design shear (τv vs τc) using conservative τc table (approx)
10) minimum reinforcement
11) cracking check (simple heuristic)
12) distribution reinforcement (recommendation)
13) shear stress checks (again τv vs τc)
14) deflection check (simple L/d with placeholder for modification factors)
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
    clamp,
    round_up
)
from .reinforcement import recommend_bars

# ---------------------------------------------------------
# Helper: approximate τc table (Table 19 IS 456) - conservative values
# NOTE: These are conservative approximations. If you want exact IS table
# numbers we can paste the table and interpolate exactly.
# Format: (fck: (τc in N/mm2 for different percentages of steel or shear cases))
# Here we use single values as conservative τc for typical slab (for design shear)
# ---------------------------------------------------------
TC_APPROX = {
    20: 0.28,  # MPa (conservative)
    25: 0.3,
    30: 0.33,
    35: 0.36,
    40: 0.38
}

# Cracking and deflection constants (placeholders / heuristics)
CRACKING_AST_RATIO_LIMIT = 0.002  # crude heuristic: if Ast/bd < this, cracking likely
DISTRIBUTION_PERCENT = 0.25  # 25% of main steel as distribution (typical guideline)


def solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=1000, fck=DEFAULT_FCK, fy=DEFAULT_FY):
    """
    Iteratively solve Ast using IS 456 stress block (singly reinforced).
    Returns Ast (mm2 per metre).
    """
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
    fy=DEFAULT_FY,
    exposure="Moderate"
):
    """
    Implements the college procedure and returns:
    - result dict (summary)
    - detailed_steps list for UI (each step is dict with title & body)
    """

    detailed_steps = []
    warnings = []

    # -------------------------
    # Step 0: Inputs summary
    # -------------------------
    detailed_steps.append({
        "title": "Inputs summary",
        "body": (
            f"Clear span Lc = {clear_span_m:.3f} m\n"
            f"Support width = {support_width_m:.3f} m\n"
            f"Live load = {live_load_kN_m2:.3f} kN/m²\n"
            f"Floor finish = {floor_finish_kN_m2:.3f} kN/m²\n"
            f"Partition load (line) = {partitions_kN_per_m:.3f} kN/m\n"
            f"Concrete grade fck = {fck} MPa, Steel fy = {fy} MPa\n"
            f"Nominal cover = {cover_mm} mm, Bar dia = {bar_dia_mm} mm\n"
            f"Exposure: {exposure}\n"
        )
    })

    # -------------------------
    # Step 1: Check one-way vs two-way
    # -------------------------
    # For one-way decision we need Ly & Lx; in one-way function caller we assume this is a
    # local strip of width 1m so user should call two-way separately.
    # For completeness, we include a ratio check if support_width provided as Ly: Lx unknown here.
    # We record that this function assumes one-way design (caller decides).
    detailed_steps.append({
        "title": "One-way / Two-way check",
        "body": "This module performs one-way slab design. Use Two-Way module separately when Ly/Lx <= 2 and slab supported on four sides."
    })

    # -------------------------
    # Step 2 & 3: Initial depth and nominal cover based on exposure
    # -------------------------
    # Initial effective depth from L/d (user chosen); L/d default provided by L_div_d
    d_initial_mm = max((clear_span_m * 1000.0) / L_div_d, 100.0)
    detailed_steps.append({
        "title": "Initial effective depth (from L/d)",
        "body": f"Using L/d = {L_div_d}, initial effective depth d_initial = {d_initial_mm:.1f} mm"
    })

    # Nominal cover recommendation based on exposure (simple mapping)
    if exposure.lower().startswith("moder"):
        cover_rec_mm = max(cover_mm, 20)
    elif exposure.lower().startswith("sever"):
        cover_rec_mm = max(cover_mm, 25)
    else:
        cover_rec_mm = max(cover_mm, 30)

    detailed_steps.append({
        "title": "Nominal cover",
        "body": f"Recommended nominal cover for exposure '{exposure}': {cover_rec_mm} mm (user provided: {cover_mm} mm)"
    })

    # -------------------------
    # Step 4: Effective span (IS 456 Clause 22.2)
    # -------------------------
    # Effective span = min(clear_span + d, centre-to-centre)
    centre_to_centre = clear_span_m + support_width_m
    clear_plus_d = clear_span_m + (d_initial_mm / 1000.0)
    L_eff = min(clear_plus_d, centre_to_centre)
    detailed_steps.append({
        "title": "Effective span",
        "body": (
            f"Centre-to-centre span = {centre_to_centre:.3f} m\n"
            f"Clear span + d = {clear_plus_d:.3f} m\n"
            f"Effective span (min of above) = {L_eff:.3f} m"
        )
    })

    # Recompute depth using final effective span (iterate once)
    d_mm = max((L_eff * 1000.0) / L_div_d, 100.0)
    D_mm = d_mm + cover_rec_mm + (bar_dia_mm / 2.0)
    detailed_steps.append({
        "title": "Final effective & overall depth",
        "body": f"Final effective depth d = {d_mm:.1f} mm; overall depth D = {D_mm:.1f} mm"
    })

    # -------------------------
    # Step 5: Factored load
    # -------------------------
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

    # -------------------------
    # Step 6: Ultimate moment and shear
    # -------------------------
    Mu_kN_m = wu_kN_per_m * (L_eff ** 2) / 8.0  # simply supported
    Mu_Nmm = moment_kNm_to_Nmm(Mu_kN_m)
    Vu_kN = wu_kN_per_m * L_eff / 2.0  # shear at support per metre
    Vu_N = Vu_kN * 1000.0
    detailed_steps.append({
        "title": "Ultimate bending moment & shear",
        "body": (
            f"Mu = w_u * L^2 / 8 = {Mu_kN_m:.3f} kN·m per metre\n"
            f"Vu (at support) = w_u * L / 2 = {Vu_kN:.3f} kN per metre"
        )
    })

    # -------------------------
    # Step 7: Maximum depth check (practical)
    # -------------------------
    # Practical limit: we avoid excessive depth, but IS doesn't give a simple absolute max.
    # We'll warn if D > 500 mm (practical).
    if D_mm > 500:
        warnings.append(f"Overall depth D = {D_mm:.1f} mm is large (>500 mm). Consider deeper beams or alternate solution.")
    detailed_steps.append({
        "title": "Maximum depth check",
        "body": f"Overall depth D = {D_mm:.1f} mm (warning if > 500 mm)."
    })

    # -------------------------
    # Step 8: Reinforcement in slab (Ast)
    # -------------------------
    b_mm = 1000.0
    ast_req = solve_ast_from_mu(Mu_Nmm, d_mm, b_mm=b_mm, fck=fck, fy=fy)
    detailed_steps.append({
        "title": "Required tension steel (Ast)",
        "body": f"Ast required (per metre) = {ast_req:.2f} mm²/m"
    })

    # -------------------------
    # Step 9: Design of shear (τv) vs τc
    # -------------------------
    # compute shear stress τv = Vu / (b*d) in N/mm2
    d_eff_mm = d_mm
    Av = b_mm * d_eff_mm  # mm2 (for 1m width)
    tau_v = (Vu_N) / Av  # N/mm2
    tau_c = TC_APPROX.get(fck, 0.3)  # conservative
    detailed_steps.append({
        "title": "Shear check (compare τv with τc)",
        "body": (
            f"Design shear stress τv = Vu/(b*d) = {tau_v:.4f} N/mm²\n"
            f"Conservative τc used (approx from Table 19) for fck={fck} MPa: τc = {tau_c:.3f} N/mm²\n"
            f"If τv > τc, provide web reinforcement / check punching/shear design."
        )
    })
    if tau_v > tau_c:
        warnings.append(f"Shear stress τv = {tau_v:.4f} N/mm² exceeds conservative τc = {tau_c:.3f} N/mm² -> Provide shear reinforcement or redesign.")

    # -------------------------
    # Step 10: Minimum reinforcement
    # -------------------------
    ast_min = MIN_REINFORCEMENT_RATIO * b_mm * d_mm
    min_flag = False
    if ast_req < ast_min:
        ast_req = ast_min
        min_flag = True
        detailed_steps.append({
            "title": "Minimum reinforcement applied",
            "body": f"Ast required increased to minimum Ast_min = {ast_min:.2f} mm²/m"
        })
    else:
        detailed_steps.append({
            "title": "Minimum reinforcement",
            "body": f"Ast_min = {ast_min:.2f} mm²/m; Ast_required already >= min."
        })

    # -------------------------
    # Step 11: Cracking check (simple)
    # -------------------------
    # Use simple heuristic: Ast/(b*d) ratio compared to threshold.
    ast_ratio = ast_req / (b_mm * d_mm)
    cracking_msg = f"Ast/(b*d) = {ast_ratio:.5f}"
    if ast_ratio < CRACKING_AST_RATIO_LIMIT:
        cracking_msg += " -> Low steel ratio; cracking likely. Consider increasing Ast or using closer bars."
        warnings.append("Cracking: calculated steel ratio is low — serviceability cracking may occur.")
    detailed_steps.append({"title": "Cracking check", "body": cracking_msg})

    # -------------------------
    # Step 12: Distribution reinforcement
    # -------------------------
    # Recommend distribution steel = some fraction of main steel (typical)
    dist_ast = DISTRIBUTION_PERCENT * ast_req
    detailed_steps.append({
        "title": "Distribution reinforcement recommendation",
        "body": f"Recommend distribution steel (secondary direction) ≈ {DISTRIBUTION_PERCENT*100:.0f}% of main Ast = {dist_ast:.2f} mm²/m"
    })

    # -------------------------
    # Step 13: Check for shear stress again (summarized)
    # -------------------------
    detailed_steps.append({
        "title": "Shear stress summary",
        "body": f"τv = {tau_v:.4f} N/mm²; τc (approx) = {tau_c:.3f} N/mm²"
    })

    # -------------------------
    # Step 14: Deflection check (simple L/d and placeholder for mod factors)
    # -------------------------
    ld_ratio = L_eff * 1000.0 / d_mm
    # basic allowable (simply supported) = 20
    allowed_basic = 20.0
    defl_msg = f"Computed L/d = {ld_ratio:.2f}. Basic allowable (simply supported) = {allowed_basic}."
    if ld_ratio > allowed_basic:
        defl_msg += " L/d exceeds basic allowable. Serviceability deflection may govern."
        warnings.append("Deflection: L/d exceeds basic allowable. Consider increasing depth or check modification factors.")
    detailed_steps.append({"title": "Deflection (basic check)", "body": defl_msg})

    # Note: If you want full IS 456 modification-factor method (Kt, Kc), we can implement next.

    # -------------------------
    # Spacing & bar selection
    # -------------------------
    # recommend bars using reinforcement.recommend_bars
    recommend = recommend_bars(ast_req)
    detailed_steps.append({
        "title": "Bar selection candidates (recommended)",
        "body": f"Top recommendation: {recommend['recommended']}\nAll candidates: {recommend['candidates']}"
    })

    # compute spacing for the selected bar (recommended choice)
    rec = recommend['recommended']
    spacing_mm = rec.get("spacing_mm", None)
    bar_dia_sel = rec.get("bar_dia_mm", None)
    ast_provided = rec.get("Ast_provided_mm2_per_m", None)

    # warnings about min spacing & max spacing already included in recommend_bars warnings
    if not rec.get("ok", True):
        for w in rec.get("warnings", []):
            warnings.append(f"Bar recommendation warning: {w}")

    # final packaged result
    result = {
        "slab_type": "One-way (detailed procedure)",
        "clear_span_m": round(clear_span_m, 3),
        "effective_span_m": round(L_eff, 3),
        "cover_mm": cover_rec_mm,
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
        "tau_c_used_N_per_mm2": round(tau_c, 3),
        "ld_ratio": round(ld_ratio, 2),
        "fck": fck,
        "fy": fy,
        "warnings": warnings,
        "detailed_steps": detailed_steps
    }

    return result
