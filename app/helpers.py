from .constants import DEFAULT_WIDTH, UNIT_WEIGHT_CONCRETE if False else None  # placeholder, we will define below
# We'll define unit weight here directly to avoid circular import
UNIT_WEIGHT_CONCRETE = 25.0  # kN/m3
GAMMA_F = 1.5

def effective_span_clear(L, support_width):
    return max(L, (L + support_width) / 2.0)

def slab_self_weight(thickness_mm):
    thickness_m = thickness_mm / 1000.0
    return UNIT_WEIGHT_CONCRETE * thickness_m

def total_dead_load(self_weight, floor_finish, partitions):
    return self_weight + floor_finish + partitions

def factored_load(dead_load, live_load):
    return GAMMA_F * (dead_load + live_load)

def clamp(value, mn, mx):
    return max(mn, min(value, mx))
