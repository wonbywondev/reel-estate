"""TTS 서버(tts_server/)를 호출해 텍스트를 MP3 파일로 저장한다."""
import os
from pathlib import Path

import requests

TTS_SERVER_URL = os.environ.get("TTS_SERVER_URL", "http://localhost:8000")


def text_to_speech(text: str, save_path: str) -> str:
    """TTS 서버에 텍스트를 보내 MP3로 저장한다.

    Returns:
        저장된 파일 경로

    Raises:
        RuntimeError: 서버 호출 실패 시
    """
    resp = requests.post(
        f"{TTS_SERVER_URL}/synthesize",
        json={"text": text},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"TTS 서버 오류 {resp.status_code}: {resp.text}")
    Path(save_path).write_bytes(resp.content)
    return save_path
