import os
import requests
from io import BytesIO

from PIL import Image
from dotenv import load_dotenv

load_dotenv()

STATIC_MAP_URL = "https://maps.apigw.ntruss.com/map-static/v2/raster"
MAP_W = 1080
MAP_H = 608  # 슬라이드 내 지도 영역 (9:16 프레임 안에 들어갈 크기)


def download_static_map(
    lat: float,
    lng: float,
    subway_list: list[dict],
    save_path: str,
) -> str:
    """Static Map PNG를 다운로드하고 지하철 도보 거리 텍스트를 오버레이한 후 저장한다.

    Args:
        subway_list: find_nearby_subways() 반환값 (최대 3개)

    Returns:
        저장된 파일 경로
    """
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    # 매물 위치(빨강) + 각 지하철역(파랑)을 markers로 추가
    params: list[tuple[str, str | int]] = [
        ("center", f"{lng},{lat}"),
        ("level", 15),
        ("w", MAP_W),
        ("h", MAP_H),
        ("format", "png"),
        ("markers", f"type:d|size:mid|pos:{lng} {lat}|color:red"),
    ]
    for s in subway_list:
        params.append(("markers", f"type:d|size:mid|pos:{s['lng']} {s['lat']}|color:blue"))

    resp = requests.get(STATIC_MAP_URL, params=params, headers=headers)
    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGB")
    img.save(save_path, "PNG")
    return save_path


def download_static_map_wide(
    lat: float,
    lng: float,
    save_path: str,
) -> str:
    """넓은 축척 Static Map PNG를 다운로드한다 (동네 위치 파악용).

    level=12로 더 넓은 시야, 매물 마커 1개만 표시, 지하철 오버레이 없음.

    Returns:
        저장된 파일 경로
    """
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    params: list[tuple[str, str | int]] = [
        ("center", f"{lng},{lat}"),
        ("level", 12),
        ("w", MAP_W),
        ("h", MAP_H),
        ("format", "png"),
        ("markers", f"type:d|size:mid|pos:{lng} {lat}|color:red"),
    ]

    resp = requests.get(STATIC_MAP_URL, params=params, headers=headers)
    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGB")
    img.save(save_path, "PNG")
    return save_path


