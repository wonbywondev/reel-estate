"""로컬 CSV 데이터에서 지하철역 목록을 로드한다."""
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "data" / "subway"


@dataclass(frozen=True)
class Station:
    name: str   # 예: "센트럴파크역"
    line: str   # 예: "인천1호선"
    lat: float
    lng: float


@lru_cache(maxsize=1)
def load_stations() -> list[Station]:
    """모든 CSV에서 역 정보를 로드해 반환한다. 중복은 (name, line) 기준으로 제거."""
    stations: dict[tuple[str, str], Station] = {}

    _load_seoul_1_8(stations)
    _load_seoul_9(stations)
    _load_korail_line2(stations)
    _load_incheon_yeonsu(stations)

    return list(stations.values())


def find_nearby_stations(lat: float, lng: float, radius_m: float = 3000) -> list[Station]:
    """주어진 좌표에서 radius_m 이내의 역을 거리순으로 반환한다."""
    result = []
    for station in load_stations():
        d = _haversine(lat, lng, station.lat, station.lng)
        if d <= radius_m:
            result.append((d, station))
    result.sort(key=lambda x: x[0])
    return [s for _, s in result]


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 직선 거리(m)를 반환한다."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _add(stations: dict, name: str, line: str, lat: float, lng: float) -> None:
    key = (name, line)
    if key not in stations:
        stations[key] = Station(name=name, line=line, lat=lat, lng=lng)


def _load_seoul_1_8(stations: dict) -> None:
    path = DATA_DIR / "서울교통공사_1_8호선 역사 좌표(위경도) 정보_20250814.csv"
    if not path.exists():
        return
    with open(path, encoding="cp949") as f:
        for row in csv.DictReader(f):
            try:
                _add(stations,
                     name=row["역명"] + "역",
                     line=row["호선"] + "호선",
                     lat=float(row["위도"]),
                     lng=float(row["경도"]))
            except (ValueError, KeyError):
                continue


def _load_seoul_9(stations: dict) -> None:
    path = DATA_DIR / "서울교통공사_9호선 2_3단계 역사 좌표(위경도) 정보_20260131.csv"
    if not path.exists():
        return
    with open(path, encoding="cp949") as f:
        for row in csv.DictReader(f):
            try:
                name = row["역명"]
                if not name.endswith("역"):
                    name += "역"
                _add(stations,
                     name=name,
                     line="9호선",
                     lat=float(row["위도"]),
                     lng=float(row["경도"]))
            except (ValueError, KeyError):
                continue


def _load_korail_line2(stations: dict) -> None:
    path = DATA_DIR / "국가철도공단_수도권2호선_역위치_20240624.csv"
    if not path.exists():
        return
    with open(path, encoding="cp949") as f:
        for row in csv.DictReader(f):
            try:
                name = row["역명"]
                if not name.endswith("역"):
                    name += "역"
                _add(stations,
                     name=name,
                     line=row["선명"],
                     lat=float(row["위도"]),
                     lng=float(row["경도"]))
            except (ValueError, KeyError):
                continue


def _load_incheon_yeonsu(stations: dict) -> None:
    path = DATA_DIR / "인천광역시 연수구_지하철역 현황_20250806.csv"
    if not path.exists():
        return
    with open(path, encoding="cp949") as f:
        for row in csv.DictReader(f):
            try:
                name = row["지하철역"]
                if not name.endswith("역"):
                    name += "역"
                _add(stations,
                     name=name,
                     line=row["노선"],
                     lat=float(row["위도"]),
                     lng=float(row["경도"]))
            except (ValueError, KeyError):
                continue
