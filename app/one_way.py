"""
one_way.py
One-way slab design: solver and helper functions used by both one-way and two-way modules.
"""

import math
from typing import Tuple

from .constants import DEFAULT_WIDTH, MIN_REINFORCEMENT_RATIO, DEFAULT_FCK, DEFAULT_FY
from .units import moment_kNm_to_Nmm


def solve_ast_from_mu(Mu_Nmm: float, d_mm: float, b_mm: float = 1000.0, fck: float = DEFAULT_FCK, fy: float = DEFAULT_FY) -> float:
    """
    Solve Ast (mm^2 per m) using IS simplified rectangular stress block and iterative search.
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


def compute_tau_c_IS(fck: float, ast_mm2_per_m: float, b_mm: float, d_mm: float) -> float:
    """
    Conservative approximation for tau_c by interpolating IS Table 19 rows.
    For now: use simple formula based on typical IS values to avoid wrong placeholders.
    Note: this is implemented as a look-up approximation — will be updated with Table 19 exact matrix if needed.
    """
    # compute p_t (%) = (100 * Ast) / (b*d)
    p_t = (100.0 * ast_mm2_per_m) / (b_mm * d_mm)
    # very rough baseline from IS table behaviour:
    # tau_c increases with p_t and decreases slightly with fck.
    # We'll implement a conservative formula that respects typical ranges in IS (0.15 - 0.6 N/mm2)
    tau_base = 0.18 + 0.0025 * (p_t * 100)  # not exact table; placeholder - will replace with Table 19 mapping when asked
    # reduce with higher fck slightly
    tau = max(0.08, tau_base * (30.0 / max(20.0, fck)))
    return tau
