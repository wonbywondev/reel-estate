from dataclasses import dataclass, field
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
    loan_available: bool = False
    agent_comment: Optional[str] = None
    interior_paths: list[str] = field(default_factory=list)
    interior_labels: list[str] = field(default_factory=list)
    shops_info: list[dict] = field(default_factory=list)
    facing: Optional[str] = None       # 방향 (예: 남향)
    room_config: Optional[str] = None  # 방 구성 (예: 방2 거실1 화장실1)
