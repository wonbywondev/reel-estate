"""로컬 역 DB + Naver Directions API로 가장 가까운 지하철역을 찾는다."""
import os
import requests
from dotenv import load_dotenv

from .station_db import find_nearby_stations

load_dotenv()

DIRECTION_URL = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
SEARCH_RADIUS_M = 3000   # 로컬 DB 1차 필터 반경
EXTRA_RADIUS_M = 500     # 가장 가까운 역 거리 + 이 값 이내만 최종 포함
MAX_RESULTS = 3


def find_nearby_subways(lat: float, lng: float) -> list[dict]:
    """주변 지하철역을 호선별 1개씩, 거리순 최대 3개 반환한다.

    가장 가까운 역의 경로 거리 + 500m 이내인 역만 포함.

    Returns:
        [{"station": "센트럴파크역 인천1호선", "walk_min": 5, "walk_m": 400}, ...]
    """
    candidates = find_nearby_stations(lat, lng, radius_m=SEARCH_RADIUS_M)
    if not candidates:
        raise ValueError("주변 지하철역을 찾을 수 없습니다.")

    results = []
    for station in candidates:
        try:
            distance_m, duration_ms = _driving_route(lat, lng, station.lat, station.lng)
        except Exception:
            continue
        results.append({
            "station": f"{station.name} {station.line}",
            "walk_min": round(duration_ms / 60000),
            "walk_m": distance_m,
        })

    if not results:
        raise ValueError("경로를 계산할 수 없습니다.")

    results.sort(key=lambda x: x["walk_m"])
    nearest_m = results[0]["walk_m"]
    cutoff = nearest_m + EXTRA_RADIUS_M

    # cutoff 이내 + 호선별 1개 + 최대 3개
    seen_lines: set[str] = set()
    deduped = []
    for r in results:
        if r["walk_m"] > cutoff:
            break
        line = r["station"].split()[-1]  # 마지막 토큰이 호선명
        if line not in seen_lines:
            seen_lines.add(line)
            deduped.append(r)
        if len(deduped) == MAX_RESULTS:
            break

    return deduped


def _driving_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[int, int]:
    """경로 거리(m)와 시간(ms) 반환."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(
        DIRECTION_URL,
        params={
            "start": f"{start_lng},{start_lat}",
            "goal": f"{end_lng},{end_lat}",
            "option": "traoptimal",
        },
        headers=headers,
    )
    resp.raise_for_status()
    summary = resp.json()["route"]["traoptimal"][0]["summary"]
    return summary["distance"], summary["duration"]
