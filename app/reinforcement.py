"""
reinforcement.py
-----------------
Helpers for choosing bar diameters and spacing for slab reinforcement.
All results are per metre strip (mm^2/m).
"""

import math
from typing import List, Dict, Tuple

from .constants import MIN_BAR_DIAMETER, MAX_BAR_SPACING
# reasonable minimum clear spacing (mm) between bars (practical)
MIN_CLEAR_SPACING = 20


def area_of_bar(dia_mm: float) -> float:
    """Area of single bar in mm^2 for given diameter."""
    return (math.pi * dia_mm * dia_mm) / 4.0


def min_spacing_for_dia(dia_mm: float) -> float:
    """
    Minimum clear spacing recommended:
    Usually taken as max(1.5*dia, 20 mm) for slabs (practical rule).
    This returns centre-to-centre min spacing (i.e. add dia to get c-c if you want),
    but in our usage we compare centre-to-centre spacing directly.
    """
    return max(1.5 * dia_mm, MIN_CLEAR_SPACING)


def spacing_for_ast(ast_req_mm2_per_m: float, bar_dia_mm: float) -> float:
    """
    Compute required centre-to-centre spacing (mm) for the chosen bar diameter
    to achieve ast_req (mm^2 per metre).

    spacing_mm = (area_single_bar * 1000) / ast_req
    """
    As = area_of_bar(bar_dia_mm)
    if ast_req_mm2_per_m <= 0:
        return float('inf')
    spacing_mm = (As * 1000.0) / ast_req_mm2_per_m
    return spacing_mm


def check_spacing_rules(spacing_mm: float, bar_dia_mm: float) -> Tuple[bool, List[str]]:
    """
    Check spacing against simple rules:
    - spacing <= MAX_BAR_SPACING
    - spacing >= min_spacing_for_dia
    Returns (is_ok, warnings)
    """
    warnings = []
    ok = True

    min_sp = min_spacing_for_dia(bar_dia_mm)
    if spacing_mm < min_sp:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm less than practical minimum {min_sp:.0f} mm for bar {bar_dia_mm} mm.")
    if spacing_mm > MAX_BAR_SPACING:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm exceeds IS maximum {MAX_BAR_SPACING} mm.")

    # also require bar diameter not smaller than MIN_BAR_DIAMETER
    if bar_dia_mm < MIN_BAR_DIAMETER:
        ok = False
        warnings.append(f"Bar diameter {bar_dia_mm} mm is below minimum recommended {MIN_BAR_DIAMETER} mm.")

    return ok, warnings


def recommend_bars(
    ast_req_mm2_per_m: float,
    preferred_bars: List[int] = [8, 10, 12, 16, 20, 25],
    prefer_closer_spacing: bool = True
) -> Dict:
    """
    Given required steel area per metre (Ast_req), evaluate candidate bar diameters
    and return a recommendation.

    Strategy:
    - For each bar diameter, compute spacing needed.
    - Round spacing to practical 5 mm steps and enforce integer mm.
    - Apply min spacing and max spacing rules.
    - Score candidates preferring:
        * spacing within min..max
        * spacing not extremely close (< 100 mm) unless prefer_closer_spacing True
        * fewer bars (larger dia) if spacing still OK

    Returns a dictionary with:
    {
      "candidates": [ {dia, spacing, provided_ast, ok, warnings}, ... ],
      "recommended": {dia, spacing, provided_ast, warnings}
    }
    """
    candidates = []

    for dia in preferred_bars:
        As = area_of_bar(dia)
        raw_spacing = spacing_for_ast(ast_req_mm2_per_m, dia)
        if raw_spacing == float('inf'):
            spacing = float('inf')
        else:
            # round to nearest 5 mm up (practical)
            spacing = int(math.ceil(raw_spacing / 5.0) * 5)
            if spacing < 5:
                spacing = 5

        # clamp spacing to max allowed but keep original for warnings
        prov_spacing = min(spacing, MAX_BAR_SPACING)
        provided_ast = As * (1000.0 / prov_spacing) if prov_spacing > 0 else 0.0

        ok, warnings = check_spacing_rules(prov_spacing, dia)

        candidates.append({
            "bar_dia_mm": dia,
            "spacing_mm": int(prov_spacing) if prov_spacing != float('inf') else None,
            "raw_spacing_mm": raw_spacing if raw_spacing != float('inf') else None,
            "Ast_provided_mm2_per_m": round(provided_ast, 2),
            "ok": ok,
            "warnings": warnings
        })

    # Pick recommended candidate using a simple scoring:
    # prefer ok candidates, then prefer spacing between 100 and 200 mm, then smaller number of bars (larger dia)
    def score(c):
        s = 0
        s += 100 if c["ok"] else 0
        sp = c["spacing_mm"] or 9999
        # ideal spacing bucket
        if 80 <= sp <= 200:
            s += 50
        # avoid extremely close spacing
        if sp < 80:
            s -= 10
        # prefer fewer bars (bigger dia) -> higher dia gets slight bonus
        s += c["bar_dia_mm"] / 10.0
        return s

    recommended = max(candidates, key=score)

    return {
        "candidates": candidates,
        "recommended": recommended,
        "Ast_required_mm2_per_m": round(ast_req_mm2_per_m, 2)
    }

