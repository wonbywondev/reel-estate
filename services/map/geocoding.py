import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEOCODE_URL = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"


def geocode(address: str) -> tuple[float, float]:
    """도로명 주소를 (위도, 경도)로 변환한다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(GEOCODE_URL, params={"query": address}, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("addresses"):
        raise ValueError(f"주소를 찾을 수 없습니다: {address}")
    addr = data["addresses"][0]
    return float(addr["y"]), float(addr["x"])  # (lat, lng)
