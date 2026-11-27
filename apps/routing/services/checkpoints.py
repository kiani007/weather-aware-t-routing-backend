from datetime import datetime, timedelta

from apps.core.geo import interpolate

from ..domain import CheckpointSample, RoutePath


def sample_checkpoints(path: RoutePath, interval_miles: float, departure: datetime) -> list[CheckpointSample]:
    """Walks the route and drops a checkpoint every `interval_miles`, plus origin and destination.

    Each checkpoint carries the truck's ETA there and the share of route miles it represents
    (half the distance to each neighbour), so risk can be expressed in miles.
    """
    targets = _target_miles(path.distance_miles, interval_miles)
    samples: list[CheckpointSample] = []
    travelled_miles = travelled_seconds = 0.0
    target_index = 0

    for i, (seg_miles, seg_seconds) in enumerate(zip(path.segment_miles, path.segment_seconds)):
        while target_index < len(targets) and targets[target_index] <= travelled_miles + seg_miles:
            fraction = (targets[target_index] - travelled_miles) / seg_miles if seg_miles else 0.0
            samples.append(
                CheckpointSample(
                    sequence=target_index,
                    coordinate=interpolate(path.coordinates[i], path.coordinates[i + 1], fraction),
                    mile_marker=targets[target_index],
                    eta=departure + timedelta(seconds=travelled_seconds + seg_seconds * fraction),
                )
            )
            target_index += 1
        travelled_miles += seg_miles
        travelled_seconds += seg_seconds

    if target_index < len(targets):
        samples.append(
            CheckpointSample(
                sequence=target_index,
                coordinate=path.coordinates[-1],
                mile_marker=path.distance_miles,
                eta=departure + timedelta(seconds=path.duration_seconds),
            )
        )
    return _with_represented_miles(samples)


def _target_miles(total: float, interval: float) -> list[float]:
    targets = [i * interval for i in range(int(total // interval) + 1)]
    if total - targets[-1] > 1e-6:
        targets.append(total)
    return targets


def _with_represented_miles(samples: list[CheckpointSample]) -> list[CheckpointSample]:
    result = []
    for i, sample in enumerate(samples):
        before = (sample.mile_marker - samples[i - 1].mile_marker) / 2 if i > 0 else 0.0
        after = (samples[i + 1].mile_marker - sample.mile_marker) / 2 if i < len(samples) - 1 else 0.0
        result.append(
            CheckpointSample(sample.sequence, sample.coordinate, sample.mile_marker, sample.eta, before + after)
        )
    return result
