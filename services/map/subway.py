import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
DIRECTION_URL = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
SEARCH_RADIUS = 500  # 미터


def find_nearest_subway(lat: float, lng: float) -> dict:
    """반경 500m 내 지하철역 중 도보 거리가 가장 짧은 역을 반환한다.

    Returns:
        {"station": "강남역", "walk_min": 5, "walk_m": 400}
    """
    stations = _search_nearby_stations(lat, lng)
    if not stations:
        raise ValueError(f"반경 {SEARCH_RADIUS}m 내 지하철역을 찾을 수 없습니다.")

    best = None
    best_duration = float("inf")

    for station in stations:
        s_lat = float(station["mapy"]) / 1e7
        s_lng = float(station["mapx"]) / 1e7
        try:
            distance_m, duration_ms = _walking_route(lat, lng, s_lat, s_lng)
        except Exception:
            continue
        if duration_ms < best_duration:
            best_duration = duration_ms
            best = {
                "station": station["title"].replace("<b>", "").replace("</b>", ""),
                "walk_min": round(duration_ms / 60000),
                "walk_m": distance_m,
            }

    if best is None:
        raise ValueError("도보 경로를 계산할 수 없습니다.")
    return best


def _search_nearby_stations(lat: float, lng: float) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(
        SEARCH_URL,
        params={"query": "지하철역", "display": 5, "sort": "comment", "coordinate": f"{lng},{lat}"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def _walking_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[int, int]:
    """도보 경로 거리(m)와 시간(ms) 반환."""
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
