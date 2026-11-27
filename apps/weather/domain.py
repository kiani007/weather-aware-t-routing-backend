import bisect
from dataclasses import dataclass
from datetime import datetime

from apps.risk.domain import WeatherConditions


@dataclass(frozen=True)
class HourlySeries:
    """Hourly forecast for one location; times are unix seconds (UTC)."""

    times: tuple[int, ...]
    wind_mph: tuple[float, ...]
    rain_in_hr: tuple[float, ...]
    snow_in_hr: tuple[float, ...]

    def at(self, moment: datetime) -> WeatherConditions | None:
        """Linearly interpolates between the surrounding hours; None outside the forecast window."""
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

    def _conditions(self, left: int, right: int, fraction: float) -> WeatherConditions:
        def blend(values: tuple[float, ...]) -> float:
            return round(values[left] + (values[right] - values[left]) * fraction, 3)

        return WeatherConditions(blend(self.wind_mph), blend(self.rain_in_hr), blend(self.snow_in_hr))
