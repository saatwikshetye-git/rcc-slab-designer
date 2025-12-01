"""
reinforcement.py
-----------------
Helpers for choosing bar diameters and spacing for slab reinforcement.
Improved candidate scoring and human-readable outputs for UI.
"""

import math
from typing import List, Dict, Tuple

from .constants import MIN_BAR_DIAMETER, MAX_BAR_SPACING

MIN_CLEAR_SPACING = 20  # mm


def area_of_bar(dia_mm: float) -> float:
    return (math.pi * dia_mm * dia_mm) / 4.0


def min_spacing_for_dia(dia_mm: float) -> float:
    return max(1.5 * dia_mm, MIN_CLEAR_SPACING)


def spacing_for_ast(ast_req_mm2_per_m: float, bar_dia_mm: float) -> float:
    As = area_of_bar(bar_dia_mm)
    if ast_req_mm2_per_m <= 0:
        return float('inf')
    spacing_mm = (As * 1000.0) / ast_req_mm2_per_m
    return spacing_mm


def check_spacing_rules(spacing_mm: float, bar_dia_mm: float) -> Tuple[bool, List[str]]:
    warnings = []
    ok = True

    min_sp = min_spacing_for_dia(bar_dia_mm)
    if spacing_mm < min_sp:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm < practical minimum {min_sp:.0f} mm for bar {bar_dia_mm} mm.")
    if spacing_mm > MAX_BAR_SPACING:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm exceeds IS maximum {MAX_BAR_SPACING} mm.")
    if bar_dia_mm < MIN_BAR_DIAMETER:
        ok = False
        warnings.append(f"Bar diameter {bar_dia_mm} mm below recommended minimum {MIN_BAR_DIAMETER} mm.")
    return ok, warnings


def recommend_bars(
    ast_req_mm2_per_m: float,
    preferred_bars: List[int] = [8, 10, 12, 16, 20, 25],
    prefer_closer_spacing: bool = True
) -> Dict:
    """
    Return a structured dictionary with candidate list and recommended option.
    Each candidate contains:
      - bar_dia_mm, spacing_mm (rounded), raw_spacing_mm, Ast_provided_mm2_per_m, ok (bool), warnings (list)
    The recommended candidate is chosen by score:
      - ok candidates preferred
      - spacing in practical band (80-200 mm) preferred
      - penalize extremely close spacing (< 80 mm) moderately (construction difficulty)
      - prefer larger diameter slightly to reduce congestion
    """
    candidates = []

    for dia in preferred_bars:
        As = area_of_bar(dia)
        raw_spacing = spacing_for_ast(ast_req_mm2_per_m, dia)
        if raw_spacing == float('inf'):
            spacing = float('inf')
        else:
            spacing = math.ceil(raw_spacing / 5.0) * 5
            spacing = max(spacing, 5)

        prov_spacing = min(spacing, MAX_BAR_SPACING) if spacing != float('inf') else MAX_BAR_SPACING
        provided_ast = As * (1000.0 / prov_spacing) if prov_spacing > 0 else 0.0

        ok, warnings = check_spacing_rules(prov_spacing, dia)

        candidates.append({
            "bar_dia_mm": int(dia),
            "spacing_mm": int(prov_spacing) if prov_spacing != float('inf') else None,
            "raw_spacing_mm": raw_spacing if raw_spacing != float('inf') else None,
            "Ast_provided_mm2_per_m": round(provided_ast, 2),
            "ok": ok,
            "warnings": warnings
        })

    # scoring
    def score(c):
        s = 0
        s += 100 if c["ok"] else 0
        sp = c["spacing_mm"] or 9999
        # ideal spacing bucket
        if 80 <= sp <= 200:
            s += 50
        # avoid too close spacing
        if sp < 80:
            s -= 20
        # prefer fewer bars (larger dia)
        s += (c["bar_dia_mm"] / 5.0)
        # penalize huge spacing (close to max)
        if sp >= MAX_BAR_SPACING:
            s -= 10
        return s

    recommended = max(candidates, key=score)

    return {
        "candidates": candidates,
        "recommended": recommended,
        "Ast_required_mm2_per_m": round(ast_req_mm2_per_m, 2)
    }
