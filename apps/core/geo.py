import math
from typing import NamedTuple

EARTH_RADIUS_MILES = 3958.8
METERS_PER_MILE = 1609.344


class Coordinate(NamedTuple):
    lat: float
    lon: float

    def rounded(self, step: float) -> "Coordinate":
        return Coordinate(round(round(self.lat / step) * step, 4), round(round(self.lon / step) * step, 4))


def haversine_miles(a: Coordinate, b: Coordinate) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def interpolate(a: Coordinate, b: Coordinate, fraction: float) -> Coordinate:
    return Coordinate(a.lat + (b.lat - a.lat) * fraction, a.lon + (b.lon - a.lon) * fraction)


def perpendicular_offset(a: Coordinate, b: Coordinate, fraction_along: float, offset_ratio: float) -> Coordinate:
    """Point at `fraction_along` the a→b chord, pushed sideways by `offset_ratio` of the chord length."""
    scale = math.cos(math.radians((a.lat + b.lat) / 2))
    dx, dy = (b.lon - a.lon) * scale, b.lat - a.lat
    base = interpolate(a, b, fraction_along)
    return Coordinate(base.lat + dx * offset_ratio, base.lon - dy * offset_ratio / scale)


def simplify(points: list[Coordinate], tolerance: float) -> list[Coordinate]:
    """Iterative Ramer–Douglas–Peucker simplification (tolerance in degrees)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        max_dist, index = 0.0, start
        for i in range(start + 1, end):
            dist = _perpendicular_distance(points[i], points[start], points[end])
            if dist > max_dist:
                max_dist, index = dist, i
        if max_dist > tolerance:
            keep[index] = True
            stack.extend(((start, index), (index, end)))
    return [p for p, k in zip(points, keep) if k]


def _perpendicular_distance(p: Coordinate, a: Coordinate, b: Coordinate) -> float:
    dx, dy = b.lon - a.lon, b.lat - a.lat
    if dx == 0 and dy == 0:
        return math.hypot(p.lon - a.lon, p.lat - a.lat)
    t = max(0.0, min(1.0, ((p.lon - a.lon) * dx + (p.lat - a.lat) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p.lon - (a.lon + t * dx), p.lat - (a.lat + t * dy))
