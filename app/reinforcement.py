"""
reinforcement.py

Helpers for bar areas, spacing and recommendations.
"""

import math
from typing import List, Dict, Tuple

from .constants import MIN_BAR_DIAMETER, MAX_BAR_SPACING

MIN_CLEAR_SPACING = 20.0  # mm (practical lower limit)

def area_of_bar_mm2(dia_mm: float) -> float:
    return math.pi * (dia_mm ** 2) / 4.0

def min_spacing_for_dia(dia_mm: float) -> float:
    # centre-to-centre spacing (practical): max(1.5*dia, 20)
    return max(1.5 * dia_mm, MIN_CLEAR_SPACING)

def spacing_for_ast(ast_req_mm2_per_m: float, dia_mm: float) -> float:
    As = area_of_bar_mm2(dia_mm)
    if ast_req_mm2_per_m <= 0:
        return float('inf')
    spacing_mm = (As * 1000.0) / ast_req_mm2_per_m
    return spacing_mm

def check_spacing(spacing_mm: float, dia_mm: float) -> Tuple[bool, List[str]]:
    warnings = []
    ok = True
    min_sp = min_spacing_for_dia(dia_mm)
    if spacing_mm < min_sp:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm less than practical minimum {min_sp:.0f} mm for bar {dia_mm} mm.")
    if spacing_mm > MAX_BAR_SPACING:
        ok = False
        warnings.append(f"Spacing {spacing_mm:.0f} mm exceeds IS max {MAX_BAR_SPACING} mm.")
    if dia_mm < MIN_BAR_DIAMETER:
        ok = False
        warnings.append(f"Bar dia {dia_mm} mm below recommended {MIN_BAR_DIAMETER} mm.")
    return ok, warnings

def recommend_bars(ast_req_mm2_per_m: float, preferred_bars: List[int] = [8, 10, 12, 16, 20, 25]) -> Dict:
    candidates = []
    for dia in preferred_bars:
        As = area_of_bar_mm2(dia)
        raw_spacing = spacing_for_ast(ast_req_mm2_per_m, dia)
        if raw_spacing == float('inf'):
            spacing = float('inf')
        else:
            spacing = int(math.ceil(raw_spacing / 5.0) * 5)
            spacing = max(spacing, 5)
        prov_spacing = min(spacing, MAX_BAR_SPACING)
        provided_ast = As * (1000.0 / prov_spacing) if prov_spacing != float('inf') and prov_spacing > 0 else 0.0
        ok, warns = check_spacing(prov_spacing, dia)
        candidates.append({
            "bar_dia_mm": dia,
            "spacing_mm": int(prov_spacing) if prov_spacing != float('inf') else None,
            "raw_spacing_mm": raw_spacing if raw_spacing != float('inf') else None,
            "Ast_provided_mm2_per_m": round(provided_ast, 2),
            "ok": ok,
            "warnings": warns
        })

    # scoring
    def score(c):
        s = 0
        s += 100 if c["ok"] else 0
        sp = c["spacing_mm"] or 9999
        if 80 <= sp <= 200:
            s += 50
        if sp < 80:
            s -= 10
        s += c["bar_dia_mm"] / 10.0
        return s

    recommended = max(candidates, key=score)
    return {"candidates": candidates, "recommended": recommended, "Ast_required_mm2_per_m": round(ast_req_mm2_per_m, 2)}

