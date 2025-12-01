"""
reinforcement.py

Simple reinforcement utility functions used by one_way.py and two_way.py

Provides:
- area_of_bar_mm2(dia_mm) -> float
- recommend_bars(ast_req_mm2_per_m, preferred_bars=[...], prefer_closer_spacing=False) -> dict

The recommend_bars() implementation is conservative and self-contained:
- computes raw spacing for each candidate bar diameter to meet Ast_required (mm^2 per m)
- rounds spacing to a practical value (to nearest 5 mm)
- computes Ast_provided for the rounded spacing
- marks candidates as ok/warning based on spacing limits and Ast coverage
- returns a "recommended" candidate (first candidate that provides >= Ast_req and has reasonable spacing),
  otherwise returns the best available candidate (largest Ast_provided).
"""

import math
from typing import List, Dict, Optional

# Practical spacing bounds (mm) used for basic checks
MIN_SPACING_MM = 50    # don't allow extremely close (practical min)
MAX_SPACING_MM = 300   # practical maximum spacing for main bars in slabs (conservative)

def area_of_bar_mm2(dia_mm: float) -> float:
    """Area of a circular bar in mm^2 given diameter in mm."""
    return math.pi * (dia_mm ** 2) / 4.0


def _round_spacing_practical(spacing_mm: float) -> int:
    """
    Round spacing to a practical constructible value.
    We choose nearest 5 mm for simplicity.
    """
    if spacing_mm is None or spacing_mm == float("inf"):
        return None
    return int(max(1, round(spacing_mm / 5.0) * 5))


def recommend_bars(
    ast_req_mm2_per_m: float,
    preferred_bars: Optional[List[int]] = None,
    prefer_closer_spacing: bool = False
) -> Dict:
    """
    Recommend bar diameter and spacing given required Ast (mm^2 per m).
    Returns a dict with keys:
      - recommended: {bar_dia_mm, spacing_mm, Ast_provided_mm2_per_m, ok, warnings}
      - candidates: list of candidate dicts (same structure)
    """
    if preferred_bars is None:
        preferred_bars = [8, 10, 12, 16, 20, 25]

    candidates = []

    # protect against zero/near-zero ast requirement
    ast_req = max(ast_req_mm2_per_m or 0.0, 0.0)

    for dia in preferred_bars:
        area = area_of_bar_mm2(dia)  # mm2 per bar
        if ast_req <= 0:
            # if no steel required, place very widely spaced bars (practical default)
            raw_spacing = 300.0
        else:
            # number of bars per metre needed = ast_req / area
            bars_per_m = ast_req / area
            if bars_per_m <= 0:
                raw_spacing = 300.0
            else:
                raw_spacing = 1000.0 / bars_per_m  # mm

        spacing_rounded = _round_spacing_practical(raw_spacing)
        # avoid division by zero
        ast_provided = (area * (1000.0 / spacing_rounded)) if spacing_rounded else 0.0

        warnings = []
        ok = True

        # check practical spacing bounds
        if spacing_rounded is None:
            ok = False
            warnings.append("Invalid spacing computed.")
        else:
            if spacing_rounded < MIN_SPACING_MM:
                ok = False
                warnings.append(f"Spacing {spacing_rounded} mm < practical minimum ({MIN_SPACING_MM} mm).")
            if spacing_rounded > MAX_SPACING_MM:
                # treat as warn but allow (very wide spacing might be used with distribution steel)
                warnings.append(f"Spacing {spacing_rounded} mm > recommended maximum ({MAX_SPACING_MM} mm).")

        # check Ast coverage
        if ast_provided + 1e-6 < ast_req:
            ok = False
            warnings.append("Provided Ast < required Ast (after rounding).")

        candidates.append({
            "bar_dia_mm": dia,
            "raw_spacing_mm": raw_spacing,
            "spacing_mm": spacing_rounded,
            "Ast_provided_mm2_per_m": ast_provided,
            "ok": ok,
            "warnings": warnings
        })

    # Choose recommended candidate:
    # Preference: candidates that are ok and provide Ast >= required.
    ok_candidates = [c for c in candidates if c["ok"] and c["Ast_provided_mm2_per_m"] >= ast_req - 1e-6]
    if ok_candidates:
        # choose the one with the largest bar dia? or with closest spacing to requirement?
        if prefer_closer_spacing:
            # pick candidate with smallest spacing among ok ones
            recommended = min(ok_candidates, key=lambda c: (c["spacing_mm"] if c["spacing_mm"] else float("inf")))
        else:
            # choose candidate with smallest bar dia that still ok (economical)
            recommended = sorted(ok_candidates, key=lambda c: (c["bar_dia_mm"], c["spacing_mm"]))[0]
    else:
        # nothing fully ok; choose candidate that gives highest Ast_provided (most conservative)
        recommended = max(candidates, key=lambda c: c["Ast_provided_mm2_per_m"])

    # Ensure recommended has consistent fields
    if "warnings" not in recommended:
        recommended["warnings"] = []
    if "ok" not in recommended:
        recommended["ok"] = recommended["Ast_provided_mm2_per_m"] >= ast_req - 1e-6

    return {
        "recommended": recommended,
        "candidates": candidates
    }
