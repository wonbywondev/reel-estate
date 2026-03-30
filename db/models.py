from dataclasses import dataclass
from typing import Optional


@dataclass
class Room:
    address: str
    floor: int
    size_pyeong: float
    deposit: int
    monthly_rent: int
    options: list[str]
    year_built: int
    id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    subway_info: Optional[list[dict]] = None  # [{"station": "강남역", "walk_min": 5, ...}]
    video_path: Optional[str] = None
    created_at: Optional[str] = None
