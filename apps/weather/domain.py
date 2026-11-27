import bisect
from dataclasses import dataclass
from datetime import datetime

from apps.risk.domain import WeatherConditions


@dataclass(frozen=True)
class HourlySeries:
    """Hourly forecast for one location; times are unix seconds (UTC).

    A value is None when the provider had no data for that hour. Missing data is
    never treated as zero: conditions that depend on it come back as None (unknown).
    """

    times: tuple[int, ...]
    wind_mph: tuple[float | None, ...]
    rain_in_hr: tuple[float | None, ...]
    snow_in_hr: tuple[float | None, ...]

    def at(self, moment: datetime) -> WeatherConditions | None:
        """Linearly interpolates between the surrounding hours; None outside the window or when data is missing."""
        ts = moment.timestamp()
        if not self.times or ts < self.times[0] or ts > self.times[-1]:
            return None
        right = bisect.bisect_left(self.times, ts)
        if self.times[right] == ts or right == 0:
            return self._conditions(right, right, 0.0)
        left = right - 1
        fraction = (ts - self.times[left]) / (self.times[right] - self.times[left])
        return self._conditions(left, right, fraction)

    def hour(self, ts: int) -> WeatherConditions | None:
        index = bisect.bisect_left(self.times, ts)
        if index < len(self.times) and self.times[index] == ts:
            return self._conditions(index, index, 0.0)
        return None

    def _conditions(self, left: int, right: int, fraction: float) -> WeatherConditions | None:
        def blend(values: tuple[float | None, ...]) -> float | None:
            a, b = values[left], values[right]
            if a is None or b is None:
                return None
            return round(a + (b - a) * fraction, 3)

        wind, rain, snow = blend(self.wind_mph), blend(self.rain_in_hr), blend(self.snow_in_hr)
        if wind is None or rain is None or snow is None:
            return None
        return WeatherConditions(wind, rain, snow)
