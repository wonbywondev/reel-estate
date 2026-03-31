"""OpenAI TTS로 텍스트를 MP3 오디오 파일로 변환한다."""
import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

VOICE = "nova"   # 밝고 친근한 여성 목소리
MODEL = "tts-1"


def text_to_speech(text: str, save_path: str) -> str:
    """텍스트를 TTS로 변환해 save_path에 MP3로 저장한다.

    Returns:
        저장된 파일 경로
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.audio.speech.create(
        model=MODEL,
        voice=VOICE,
        input=text,
    )
    Path(save_path).write_bytes(response.content)
    return save_path
