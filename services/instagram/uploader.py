"""Instagram Graph API — 릴스 자동 업로드.

업로드 흐름:
    1. 영상 공개 URL로 미디어 컨테이너 생성 (media_type=REELS)
    2. 컨테이너 처리 완료 polling (FINISHED 상태까지 최대 120초)
    3. publish

로컬 파일은 공개 URL이 없으므로:
    - serve_and_upload() 사용 시 로컬 HTTP 서버 + ngrok 터널 자동 생성
    - 이미 공개 URL이 있으면 upload_reel() 직접 호출
"""

import os
import re
import time
import threading
import http.server
import subprocess
from pathlib import Path

import requests

GRAPH_API_BASE = "https://graph.facebook.com/v22.0"



PAGE_ID = "1063342293532222"


def _get_credentials() -> tuple[str, str]:
    account_id = os.environ.get("INSTA_ACCOUNT_ID", "")
    user_token = os.environ.get("INSTA_GRAPH_API_TOKEN", "")
    if not account_id or not user_token:
        raise RuntimeError(
            "INSTA_ACCOUNT_ID, INSTA_GRAPH_API_TOKEN 환경변수를 설정하세요."
        )
    # 사용자 토큰 → 페이지 토큰 교환
    resp = requests.get(f"{GRAPH_API_BASE}/{PAGE_ID}", params={
        "access_token": user_token,
        "fields": "access_token",
    }, timeout=15)
    if not resp.ok:
        raise RuntimeError(f"페이지 토큰 교환 실패: {resp.text}")
    page_token = resp.json().get("access_token", "")
    if not page_token:
        raise RuntimeError("페이지 토큰을 가져올 수 없습니다. Facebook 페이지 연결을 확인하세요.")
    return account_id, page_token


def _create_container(
    account_id: str,
    token: str,
    video_url: str,
    caption: str = "",
) -> str:
    """미디어 컨테이너 생성 후 creation_id 반환."""
    resp = requests.post(f"{GRAPH_API_BASE}/{account_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    }, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"컨테이너 생성 실패 [{resp.status_code}]: {resp.text}")
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"컨테이너 생성 실패: {data}")
    return data["id"]


def _wait_for_container(
    token: str,
    creation_id: str,
    timeout: int = 120,
) -> None:
    """컨테이너 처리 완료(FINISHED)까지 polling."""
    url = f"{GRAPH_API_BASE}/{creation_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, params={
            "fields": "status_code,status",
            "access_token": token,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"컨테이너 처리 오류: {data}")
        time.sleep(5)
    raise TimeoutError(f"컨테이너 처리 타임아웃 ({timeout}초)")


def _publish_container(
    account_id: str,
    token: str,
    creation_id: str,
) -> str:
    """컨테이너 게시 후 media_id 반환."""
    url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
    resp = requests.post(url, data={
        "creation_id": creation_id,
        "access_token": token,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"게시 실패: {data}")
    return data["id"]


def upload_reel(video_url: str, caption: str = "") -> str:
    """공개 URL로 릴스 업로드. 게시된 media_id 반환.

    Args:
        video_url: 공개 접근 가능한 MP4 URL
        caption: 게시물 캡션 (해시태그 포함)

    Returns:
        게시된 Instagram media_id
    """
    account_id, token = _get_credentials()
    creation_id = _create_container(account_id, token, video_url, caption)
    _wait_for_container(token, creation_id)
    media_id = _publish_container(account_id, token, creation_id)
    return media_id


# ---------------------------------------------------------------------------
# 로컬 파일 서빙 (ngrok)
# ---------------------------------------------------------------------------

class _FileServer(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        _ = format, args  # 콘솔 로그 억제


import socket as _socket
import subprocess as _subprocess


def _kill_port(port: int) -> None:
    """해당 포트를 점유한 프로세스 강제 종료."""
    result = _subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
    for pid in result.stdout.strip().split("\n"):
        if pid:
            _subprocess.run(["kill", "-9", pid], capture_output=True)


def _start_local_server(directory: str, port: int) -> threading.Thread:
    _kill_port(port)
    time.sleep(0.3)

    handler = lambda *a, **kw: _FileServer(*a, directory=directory, **kw)
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(5)

    # HTTPServer를 소켓 없이 초기화한 뒤 직접 주입
    server = http.server.HTTPServer.__new__(http.server.HTTPServer)
    server.socket = sock
    server.server_address = ("", port)
    server.RequestHandlerClass = handler  # type: ignore[attr-defined]
    server.allow_reuse_address = True
    server._BaseServer__is_shut_down = threading.Event()  # type: ignore[attr-defined]
    server._BaseServer__shutdown_request = False  # type: ignore[attr-defined]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.server = server  # type: ignore[attr-defined]
    t.start()
    return t


def start_cloudflare_tunnel(port: int = 8888, timeout: int = 30) -> tuple[str, subprocess.Popen]:  # type: ignore[type-arg]
    """cloudflared 터널을 백그라운드로 실행하고 공개 URL 반환.

    Returns:
        (public_url, process) — process.terminate()로 종료
    """
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.time() + timeout
    url_pattern = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")

    while time.time() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""  # type: ignore[union-attr]
        if not line:
            time.sleep(0.1)
            continue
        match = url_pattern.search(line)
        if match:
            return match.group(0), proc

    proc.terminate()
    raise RuntimeError("cloudflared 터널 URL을 가져오지 못했습니다 (타임아웃).")


def _get_ngrok_url(port: int) -> str:
    """실행 중인 ngrok 터널에서 공개 URL 조회."""
    try:
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        tunnels = resp.json().get("tunnels", [])
        for t in tunnels:
            if str(port) in t.get("config", {}).get("addr", ""):
                return t["public_url"]
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception as e:
        raise RuntimeError(
            "ngrok이 실행 중이지 않습니다. 터미널에서 `ngrok http <port>` 실행 후 재시도하세요."
        ) from e
    raise RuntimeError("활성 ngrok 터널을 찾을 수 없습니다.")




def upload_to_r2(file_path: str, expires_in: int = 3600) -> str:
    """파일을 Cloudflare R2에 업로드하고 presigned URL 반환.

    Args:
        file_path: 업로드할 로컬 파일 경로
        expires_in: presigned URL 유효 시간 (초, 기본 1시간)

    Returns:
        presigned URL
    """
    import boto3
    endpoint = os.environ.get("R2_ENDPOINT", "")
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    bucket = os.environ.get("R2_BUCKET", "")
    if not all([endpoint, access_key, secret_key, bucket]):
        raise RuntimeError("R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET 환경변수를 설정하세요.")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    key = Path(file_path).name
    s3.upload_file(file_path, bucket, key)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return url


def reencode_for_instagram(video_path: str) -> str:
    """Instagram 요구사항에 맞게 영상 재인코딩.

    Instagram Reels 최소 스펙: H.264, 3.5Mbps 이상, AAC 128kbps 이상.
    출력 파일은 같은 디렉터리에 _ig 접미사로 저장.

    Args:
        video_path: 원본 MP4 경로

    Returns:
        재인코딩된 MP4 경로
    """
    src = Path(video_path).resolve()
    dst = src.parent / "upload_ig.mp4"
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(src),
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "3.1",
            "-b:v", "3500k",
            "-minrate", "3500k",
            "-maxrate", "3500k",
            "-bufsize", "3500k",
            "-nal-hrd", "cbr",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "48000",
            "-movflags", "+faststart",
            str(dst),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 재인코딩 실패:\n{result.stderr}")
    return str(dst)


def serve_and_upload(
    video_path: str,
    caption: str = "",
    port: int = 8888,
) -> str:
    """로컬 MP4 파일을 ngrok으로 공개 후 릴스 업로드.

    사전 조건:
        ngrok이 같은 포트로 실행 중이어야 합니다.
        터미널: `ngrok http 8888`

    Args:
        video_path: 로컬 MP4 파일 경로
        caption: 게시물 캡션
        port: 로컬 파일 서버 포트 (ngrok 포트와 일치)

    Returns:
        게시된 Instagram media_id
    """
    path = Path(video_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"파일 없음: {video_path}")

    # 로컬 HTTP 서버 시작
    thread = _start_local_server(str(path.parent), port)
    time.sleep(0.5)

    try:
        ngrok_url = _get_ngrok_url(port)
        video_url = f"{ngrok_url}/{path.name}"
        media_id = upload_reel(video_url, caption)
    finally:
        thread.server.shutdown()  # type: ignore[attr-defined]

    return media_id
