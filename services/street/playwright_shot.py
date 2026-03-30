"""Playwright으로 네이버 거리뷰 스크린샷을 찍는다. 실패 시 위성지도 fallback."""
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()


def take_street_view(lat: float, lng: float, save_path: str) -> str:
    """거리뷰 스크린샷을 찍어 save_path에 저장한다.

    Playwright으로 거리뷰를 시도하고, pano_id를 찾지 못하거나 예외가 발생하면
    위성지도 이미지로 fallback한다.

    Returns:
        저장된 파일 경로
    """
    try:
        pano_id = _get_pano_id(lat, lng)
        if pano_id:
            return _capture_street_view(pano_id, save_path)
    except Exception:
        pass

    return _fallback_satellite(lat, lng, save_path)


def _get_pano_id(lat: float, lng: float) -> str | None:
    """거리뷰 URL에서 pano_id를 추출한다."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        try:
            page.goto(
                f"https://map.naver.com/p/?c={lng},{lat},17,0,0,0,dh",
                timeout=20000,
            )
            page.wait_for_timeout(4000)
            page.get_by_role("button", name="거리뷰").click()
            page.wait_for_timeout(2000)
            popup = page.query_selector(".panorama_config_popup_btn_save")
            if popup:
                popup.click()
                page.wait_for_timeout(2000)
            page.mouse.click(700, 960)
            page.wait_for_timeout(4000)

            m = re.search(r"p=([^,&]+)", page.url)
            return m.group(1) if m else None
        finally:
            browser.close()


def _capture_street_view(pano_id: str, save_path: str) -> str:
    """pano_id로 전체화면 거리뷰 스크린샷을 찍는다."""
    sv_url = (
        f"https://map.naver.com/p?c=17.00,0,0,0,adh&isMini=false"
        f"&p={pano_id},-147,10,80,Float"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        try:
            page.goto(sv_url, timeout=20000)
            page.wait_for_timeout(5000)
            # 팝업을 JS로 숨김 (dialog끼리 겹쳐 클릭이 막히는 경우 대비)
            page.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.style.display = 'none')")
            page.wait_for_timeout(500)
            page.screenshot(path=save_path)
            return save_path
        finally:
            browser.close()


def _fallback_satellite(lat: float, lng: float, save_path: str) -> str:
    """위성지도 Static Map 이미지를 fallback으로 저장한다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    params = {
        "center": f"{lng},{lat}",
        "level": 17,
        "w": 1080,
        "h": 1920,
        "format": "png",
        "maptype": "satellite",
    }
    resp = requests.get(
        "https://maps.apigw.ntruss.com/map-static/v2/raster",
        params=params,
        headers=headers,
    )
    resp.raise_for_status()
    Path(save_path).write_bytes(resp.content)
    return save_path
