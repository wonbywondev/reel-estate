"""edge-tts 기반 한국어 TTS 합성."""
import asyncio
import io
import os

import edge_tts

VOICE = os.environ.get("TTS_VOICE", "ko-KR-SunHiNeural")


def synthesize(text: str) -> bytes:
    """텍스트를 MP3 bytes로 변환한다.

    Returns:
        MP3 bytes
    """
    return asyncio.run(_synthesize_async(text))


async def _synthesize_async(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice=VOICE)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


def load_model():
    """호환성을 위한 no-op (edge-tts는 모델 로드 불필요)."""
    pass
