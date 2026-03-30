import os
import requests
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

STATIC_MAP_URL = "https://naveropenapi.apigw.ntruss.com/map-static/v2/raster"
MAP_W = 1080
MAP_H = 608  # 슬라이드 내 지도 영역 (9:16 프레임 안에 들어갈 크기)


def download_static_map(
    lat: float,
    lng: float,
    subway_info: dict,
    save_path: str,
) -> str:
    """Static Map PNG를 다운로드하고 지하철 도보 거리 텍스트를 오버레이한 후 저장한다.

    Returns:
        저장된 파일 경로
    """
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    params = {
        "center": f"{lng},{lat}",
        "level": 15,
        "w": MAP_W,
        "h": MAP_H,
        "format": "png",
        "markers": f"type:d|size:mid|pos:{lng} {lat}|color:red",
    }
    resp = requests.get(STATIC_MAP_URL, params=params, headers=headers)
    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGBA")
    img = _draw_subway_overlay(img, subway_info)
    img.convert("RGB").save(save_path, "PNG")
    return save_path


def _draw_subway_overlay(img: Image.Image, subway_info: dict) -> Image.Image:
    """이미지 하단에 지하철역 도보 거리 텍스트를 오버레이한다."""
    text = f"지하철 {subway_info['station']} 도보 {subway_info['walk_min']}분"

    # 반투명 배경 박스
    box_h = 56
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(overlay)
    box_draw.rectangle([(0, img.height - box_h), (img.width, img.height)], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)

    # 폰트 로드 (없으면 기본 폰트 사용)
    font_path = Path("assets/fonts/NanumGothic.ttf")
    try:
        font = ImageFont.truetype(str(font_path), size=28)
    except (IOError, OSError):
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    draw.text((20, img.height - box_h + 14), text, fill=(255, 255, 255), font=font)
    return img
