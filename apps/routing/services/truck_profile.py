from dataclasses import replace

from ..domain import RoutePath


def apply_truck_speed_limit(path: RoutePath, max_speed_mph: float) -> RoutePath:
    """Car-profile durations are slowed so no segment exceeds the truck's cruising speed."""
    seconds = tuple(
        max(duration, miles / max_speed_mph * 3600) for miles, duration in zip(path.segment_miles, path.segment_seconds)
    )
    return replace(path, segment_seconds=seconds)
