"""릴스 업로드 인코딩 실험 스크립트 (Cloudflare R2).

원본 MP4를 여러 ffmpeg config로 순서대로 인코딩 → R2 업로드 → Instagram 업로드 시도.
성공하면 멈추고 성공한 config를 출력.

실행:
    python test_reel_upload.py
"""

import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from services.instagram.uploader import upload_to_r2, upload_reel

SRC = Path("output/reels_인천_연수구_컨벤시.mp4").resolve()
OUT = SRC.parent / "test_ig.mp4"

CONFIGS = [
    {
        "label": "baseline / CBR 3.5Mbps / 48kHz",
        "args": [
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
            "-b:v", "3500k", "-minrate", "3500k", "-maxrate", "3500k", "-bufsize", "3500k",
            "-nal-hrd", "cbr",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-movflags", "+faststart",
        ],
    },
    {
        "label": "main / CBR 4Mbps / 48kHz",
        "args": [
            "-c:v", "libx264", "-profile:v", "main", "-level", "4.0",
            "-b:v", "4000k", "-minrate", "4000k", "-maxrate", "4000k", "-bufsize", "4000k",
            "-nal-hrd", "cbr",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-movflags", "+faststart",
        ],
    },
    {
        "label": "high / CBR 5Mbps / 48kHz / stereo",
        "args": [
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-b:v", "5000k", "-minrate", "5000k", "-maxrate", "5000k", "-bufsize", "5000k",
            "-nal-hrd", "cbr",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
        ],
    },
    {
        "label": "copy video / AAC 재인코딩만 / 48kHz",
        "args": [
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-movflags", "+faststart",
        ],
    },
]


def reencode(args: list[str]) -> None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(SRC)] + args + [str(OUT)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패:\n{result.stderr[-500:]}")


def get_bitrate() -> str:
    import json
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(OUT)],
        capture_output=True, text=True,
    )
    br = int(json.loads(r.stdout)["format"]["bit_rate"]) // 1000
    return f"{br} kbps"


for i, cfg in enumerate(CONFIGS, 1):
    print(f"\n[{i}/{len(CONFIGS)}] 시도: {cfg['label']}")
    reencode(cfg["args"])
    print(f"       비트레이트: {get_bitrate()}")

    print(f"       R2 업로드 중...")
    try:
        video_url = upload_to_r2(str(OUT))
        print(f"       R2 URL: {video_url[:80]}...")
    except Exception as e:
        print(f"       ❌ R2 업로드 실패: {e}")
        break

    print(f"       Instagram 업로드 중...")
    try:
        media_id = upload_reel(video_url, caption="")
        print(f"\n✅ 성공! media_id: {media_id}")
        print(f"   성공한 config: {cfg['label']}")
        break
    except Exception as e:
        print(f"       ❌ 실패: {e}")
else:
    print("\n모든 config 실패.")
