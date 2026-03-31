"""네이버 Local Search API로 근처 마트/시장을 검색한다."""
import os
import math
import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"

# 카테고리별 검색 설정: (쿼리 목록, 반경 m, 최대 결과 수)
SHOP_CATEGORIES: list[tuple[list[str], int, int]] = [
    (["대형마트", "코스트코", "이마트", "홈플러스", "롯데마트", "슈퍼마켓", "전통시장", "다이소"], 10_000, 5),
    (["편의점"], 1_000, 1),
]


def find_nearby_shops(lat: float, lng: float, region_hint: str = "") -> list[dict]:
    """카테고리별 반경 내 마트/시장/편의점 목록을 반환한다.

    Returns:
        [{"name": str, "category": str, "distance": int}, ...]
        카테고리별 거리순 정렬 후 합산
    """
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_SEARCH_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_SEARCH_CLIENT_SECRET"],
    }

    result: list[dict] = []
    seen: set[str] = set()

    for queries, radius, max_count in SHOP_CATEGORIES:
        candidates: list[dict] = []

        for query in queries:
            full_query = f"{region_hint} {query}".strip() if region_hint else query
            try:
                resp = requests.get(
                    SEARCH_URL,
                    params={"query": full_query, "display": 10, "sort": "random"},
                    headers=headers,
                    timeout=5,
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])
            except Exception:
                continue

            for item in items:
                name = _strip_tags(item.get("title", ""))
                address = item.get("roadAddress") or item.get("address", "")
                category = item.get("category", "")
                mapx = item.get("mapx")
                mapy = item.get("mapy")

                if not name or name in seen:
                    continue

                if mapx and mapy:
                    shop_lng = float(mapx) / 1e7
                    shop_lat = float(mapy) / 1e7
                elif address:
                    coords = _geocode_address(address)
                    if coords is None:
                        continue
                    shop_lat, shop_lng = coords
                else:
                    continue

                distance = _haversine(lat, lng, shop_lat, shop_lng)
                if distance > radius:
                    continue

                seen.add(name)
                candidates.append({
                    "name": name,
                    "category": category,
                    "distance": int(distance),
                })

        candidates.sort(key=lambda x: x["distance"])
        result.extend(candidates[:max_count])

    return result


def _geocode_address(address: str) -> tuple[float, float] | None:
    """주소를 (lat, lng)으로 변환. 실패 시 None 반환."""
    try:
        headers = {
            "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
            "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
        }
        resp = requests.get(
            GEOCODE_URL,
            params={"query": address},
            headers=headers,
            timeout=5,
        )
        resp.raise_for_status()
        addresses = resp.json().get("addresses", [])
        if not addresses:
            return None
        addr = addresses[0]
        return float(addr["y"]), float(addr["x"])
    except Exception:
        return None


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 직선 거리(m) 반환."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _strip_tags(text: str) -> str:
    """네이버 검색 결과의 <b> 태그를 제거한다."""
    return text.replace("<b>", "").replace("</b>", "")
