import logging
from concurrent.futures import ThreadPoolExecutor

from apps.core.exceptions import UnprocessableError
from apps.core.geo import Coordinate, haversine_miles, perpendicular_offset

from ..clients import OsrmClient
from ..domain import RoutePath

logger = logging.getLogger(__name__)

VIA_OFFSETS = ((0.5, 0.18), (0.5, -0.18), (0.35, 0.3), (0.65, -0.3), (0.5, 0.4), (0.5, -0.4))
SIMILARITY_CELL_DEG = 0.02
MAX_SIMILARITY = 0.8
MAX_DETOUR_RATIO = 1.6


class RouteAlternativesService:
    """Returns up to N distinct routes: native OSRM alternatives, topped up with via-point detours."""

    def __init__(self, client: OsrmClient | None = None):
        self.client = client or OsrmClient()

    def find(self, origin: Coordinate, destination: Coordinate, count: int) -> list[RoutePath]:
        if haversine_miles(origin, destination) < 1:
            raise UnprocessableError("Origin and destination are too close together.")

        candidates = self.client.route([origin, destination], alternatives=count)
        if not candidates:
            raise UnprocessableError("No drivable route was found between these locations.")

        if len(candidates) < count:
            candidates.extend(self._via_point_candidates(origin, destination))

        routes = self._select_distinct(candidates, count)
        logger.info("Selected %d of %d route candidates", len(routes), len(candidates))
        return routes

    def _via_point_candidates(self, origin: Coordinate, destination: Coordinate) -> list[RoutePath]:
        vias = [perpendicular_offset(origin, destination, along, side) for along, side in VIA_OFFSETS]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = pool.map(lambda via: self._safe_route([origin, via, destination]), vias)
        return [path for paths in results for path in paths]

    def _safe_route(self, waypoints: list[Coordinate]) -> list[RoutePath]:
        try:
            return self.client.route(waypoints)
        except Exception:
            logger.warning("Via-point route request failed", exc_info=True)
            return []

    @staticmethod
    def _select_distinct(candidates: list[RoutePath], count: int) -> list[RoutePath]:
        fastest = min(path.duration_seconds for path in candidates)
        selected: list[tuple[RoutePath, set[tuple[int, int]]]] = []
        for path in sorted(candidates, key=lambda p: p.duration_seconds):
            if path.duration_seconds > fastest * MAX_DETOUR_RATIO:
                continue
            cells = _cells(path)
            if all(_jaccard(cells, other) < MAX_SIMILARITY for _, other in selected):
                selected.append((path, cells))
            if len(selected) == count:
                break
        return [path for path, _ in selected]


def _cells(path: RoutePath) -> set[tuple[int, int]]:
    return {(int(p.lat / SIMILARITY_CELL_DEG), int(p.lon / SIMILARITY_CELL_DEG)) for p in path.coordinates}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0
