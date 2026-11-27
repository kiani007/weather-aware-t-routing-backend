from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float
