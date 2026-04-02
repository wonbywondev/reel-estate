"""Instagram 사진 업로드 테스트 스크립트.

사전 조건:
    - ngrok http 8888 실행 중
    - .env에 INSTA_ACCOUNT_ID, INSTA_GRAPH_API_TOKEN 설정

실행:
    python test_insta_upload.py
    python test_insta_upload.py output/map_인천_연수구_컨벤시.png
"""

import os
import sys
import time
import socket
import threading
import http.server
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.environ["INSTA_ACCOUNT_ID"]
PAGE_ID = "1063342293532222"

def _get_page_token() -> str:
    user_token = os.environ["INSTA_GRAPH_API_TOKEN"]
    resp = requests.get(f"https://graph.facebook.com/v25.0/{PAGE_ID}", params={
        "access_token": user_token,
        "fields": "access_token",
    })
    return resp.json()["access_token"]

TOKEN = _get_page_token()
GRAPH_API = "https://graph.facebook.com/v25.0"
PORT = 8888


# ---------------------------------------------------------------------------
# 로컬 파일 서버
# ---------------------------------------------------------------------------

class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        _ = format, args


def _kill_port(port: int) -> None:
    result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
    for pid in result.stdout.strip().split("\n"):
        if pid:
            subprocess.run(["kill", "-9", pid], capture_output=True)


def start_file_server(directory: str, port: int) -> threading.Thread:
    _kill_port(port)
    time.sleep(0.3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(5)

    server = http.server.HTTPServer.__new__(http.server.HTTPServer)
    server.socket = sock
    server.server_address = ("", port)
    server.RequestHandlerClass = lambda *a, **kw: _SilentHandler(*a, directory=directory, **kw)  # type: ignore
    server.allow_reuse_address = True
    server._BaseServer__is_shut_down = threading.Event()  # type: ignore
    server._BaseServer__shutdown_request = False  # type: ignore

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.server = server  # type: ignore
    t.start()
    return t


# ---------------------------------------------------------------------------
# ngrok URL 조회
# ---------------------------------------------------------------------------

def get_ngrok_url(port: int) -> str:
    resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
    for tunnel in resp.json().get("tunnels", []):
        if str(port) in tunnel.get("config", {}).get("addr", ""):
            return tunnel["public_url"]
    tunnels = resp.json().get("tunnels", [])
    if tunnels:
        return tunnels[0]["public_url"]
    raise RuntimeError("ngrok 터널을 찾을 수 없습니다. `ngrok http 8888` 실행 후 재시도하세요.")


def check_url_accessible(url: str) -> None:
    resp = requests.get(url, headers={"ngrok-skip-browser-warning": "1"}, timeout=10)
    print(f"      URL 접근 확인: {resp.status_code} {resp.headers.get('content-type', '')}")


# ---------------------------------------------------------------------------
# 인스타 사진 업로드
# ---------------------------------------------------------------------------

def upload_photo(image_url: str, caption: str = "") -> str:
    print(f"  → 컨테이너 생성 중... ({image_url})")
    resp = requests.post(f"{GRAPH_API}/{ACCOUNT_ID}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": TOKEN,
    }, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"컨테이너 생성 실패 [{resp.status_code}]: {resp.text}")
    creation_id = resp.json()["id"]
    print(f"  → 컨테이너 ID: {creation_id}")

    print("  → 게시 중...")
    resp2 = requests.post(f"{GRAPH_API}/{ACCOUNT_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": TOKEN,
    }, timeout=30)
    if not resp2.ok:
        raise RuntimeError(f"게시 실패 [{resp2.status_code}]: {resp2.text}")
    media_id = resp2.json()["id"]
    print(f"  → 게시 완료! media_id: {media_id}")
    return media_id


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        next(Path("output").glob("map_wide_*.png"), None) or \
        next(Path("output").glob("map_*.png"), None)

    if not image_path or not image_path.exists():
        print("❌ 업로드할 PNG 파일이 없습니다. output/ 폴더에 PNG가 있는지 확인하세요.")
        sys.exit(1)

    # 한글 파일명 → 영문으로 복사
    safe_name = "test_upload.png"
    safe_path = image_path.parent / safe_name
    safe_path.write_bytes(image_path.read_bytes())

    print(f"[1/3] 파일 서버 시작 (포트 {PORT}): {safe_name}")
    thread = start_file_server(str(safe_path.parent), PORT)
    time.sleep(0.5)

    print("[2/3] ngrok URL 조회 중...")
    ngrok_url = get_ngrok_url(PORT)
    image_url = f"{ngrok_url}/{safe_name}"
    print(f"      공개 URL: {image_url}")

    print("[3/3] 인스타그램 업로드 중...")
    media_id = upload_photo(image_url)

    thread.server.shutdown()  # type: ignore
    print(f"\n✅ 완료! media_id: {media_id}")
