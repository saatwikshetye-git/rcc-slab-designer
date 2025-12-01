\from typing import Tuple, List

# Material defaults
DEFAULT_FCK = 25.0
DEFAULT_FY = 500.0

MIN_REINFORCEMENT_RATIO = 0.0012  # 0.12% typical
MIN_BAR_DIAMETER = 8
MAX_BAR_SPACING = 300  # mm
DEFAULT_WIDTH = 1000  # mm (1-m strip)

# Table 27 — ly/lx values and corresponding alpha_x, alpha_y (IS 456 Annex D)
TABLE27_LY_LX = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0]
TABLE27_ALPHA_X = [0.062, 0.074, 0.084, 0.093, 0.099, 0.104, 0.113, 0.118, 0.122, 0.124]
TABLE27_ALPHA_Y = [0.062, 0.061, 0.059, 0.055, 0.051, 0.046, 0.037, 0.029, 0.020, 0.014]


def interpolate_table(x_points: List[float], y_points: List[float], x: float) -> float:
    if x <= x_points[0]:
        return y_points[0]
    if x >= x_points[-1]:
        return y_points[-1]
    for i in range(len(x_points)-1):
        x0 = x_points[i]
        x1 = x_points[i+1]
        if x0 <= x <= x1:
            y0 = y_points[i]
            y1 = y_points[i+1]
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return y_points[-1]


def get_table27_alphas(ly_lx_ratio: float) -> Tuple[float, float]:
    ratio = max(min(ly_lx_ratio, TABLE27_LY_LX[-1]), TABLE27_LY_LX[0])
    ax = interpolate_table(TABLE27_LY_LX, TABLE27_ALPHA_X, ratio)
    ay = interpolate_table(TABLE27_LY_LX, TABLE27_ALPHA_Y, ratio)
    return ax, ay
