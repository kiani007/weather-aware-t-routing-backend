from dataclasses import dataclass, field
from datetime import datetime

from apps.core.geo import Coordinate


@dataclass(frozen=True)
class RoutePath:
    coordinates: tuple[Coordinate, ...]
    segment_miles: tuple[float, ...]
    segment_seconds: tuple[float, ...]
    summary: str = ""

    @property
    def distance_miles(self) -> float:
        return sum(self.segment_miles)

    @property
    def duration_seconds(self) -> float:
        return sum(self.segment_seconds)


@dataclass(frozen=True)
class CheckpointSample:
    sequence: int
    coordinate: Coordinate
    mile_marker: float
    eta: datetime
    represented_miles: float = field(default=0.0)
