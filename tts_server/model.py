"""facebook/mms-tts-kor 모델 로드 및 추론."""
import io
import numpy as np
import scipy.io.wavfile as wav
from transformers import VitsModel, AutoTokenizer
import torch

MODEL_ID = "facebook/mms-tts-kor"

_model: VitsModel | None = None
_tokenizer = None


def load_model():
    """모델을 메모리에 로드한다. 최초 1회만 실행."""
    global _model, _tokenizer
    if _model is not None:
        return
    print(f"[TTS] 모델 로딩 중: {MODEL_ID}")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    _model = VitsModel.from_pretrained(MODEL_ID)
    _model.eval()
    print("[TTS] 모델 로드 완료")


def synthesize(text: str) -> bytes:
    """텍스트를 WAV → MP3 bytes로 변환한다.

    Returns:
        MP3 bytes
    """
    if _model is None or _tokenizer is None:
        load_model()

    # uroman이 설치되어 있으면 tokenizer가 자동으로 한글 → 로마자 변환
    inputs = _tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        output = _model(**inputs).waveform

    # waveform: (1, T) float32, sample_rate: 16000
    audio = output.squeeze().numpy()
    sample_rate = _model.config.sampling_rate  # type: ignore[union-attr]

    # WAV → bytes
    wav_buf = io.BytesIO()
    audio_int16 = (audio * 32767).astype(np.int16)
    wav.write(wav_buf, sample_rate, audio_int16)
    wav_buf.seek(0)

    # WAV를 MP3로 변환 (pydub 없이 ffmpeg subprocess 사용)
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav.write(wav_buf.read())
        tmp_wav_path = tmp_wav.name

    import tempfile as tf
    tmp_mp3 = tf.mktemp(suffix=".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-q:a", "4", tmp_mp3],
        check=True,
        capture_output=True,
    )

    import os
    mp3_bytes = open(tmp_mp3, "rb").read()
    os.unlink(tmp_wav_path)
    os.unlink(tmp_mp3)
    return mp3_bytes
