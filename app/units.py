"""
units.py
--------
Helper functions for converting units commonly used in
RCC slab design. Keeps mathematical expressions clean.
"""

# ---------------------------------------------------------
# BASIC CONVERSIONS
# ---------------------------------------------------------

def mm_to_m(value_mm):
    """Convert millimetres to metres."""
    return value_mm / 1000


def m_to_mm(value_m):
    """Convert metres to millimetres."""
    return value_m * 1000


def kN_to_N(value_kN):
    """Convert kiloNewton to Newton."""
    return value_kN * 1000


def N_to_kN(value_N):
    """Convert Newton to kiloNewton."""
    return value_N / 1000


# ---------------------------------------------------------
# LOAD-RELATED HELPERS
# ---------------------------------------------------------

def kN_per_m2_to_N_per_mm2(value_kN_m2):
    """Convert kN/m² to N/mm² (rarely needed but kept for completeness)."""
    return value_kN_m2 * (1000 / 1_000_000)


def N_per_mm2_to_kN_per_m2(value_N_mm2):
    """Convert N/mm² to kN/m²."""
    return value_N_mm2 * (1_000_000 / 1000)


# ---------------------------------------------------------
# SECTION PROPERTY HELPERS
# ---------------------------------------------------------

def moment_kNm_to_Nmm(M_kNm):
    """Convert bending moment from kN·m to N·mm."""
    return M_kNm * 1_000_000


def moment_Nmm_to_kNm(M_Nmm):
    """Convert bending moment from N·mm to kN·m."""
    return M_Nmm / 1_000_000

