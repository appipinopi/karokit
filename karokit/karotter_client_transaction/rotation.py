import math


def rotate_point(x: float, y: float, radians: float) -> tuple[float, float]:
    cos_v = math.cos(radians)
    sin_v = math.sin(radians)
    return x * cos_v - y * sin_v, x * sin_v + y * cos_v
