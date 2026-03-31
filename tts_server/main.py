"""TTS FastAPI 서버.

실행:
    uv run uvicorn tts_server.main:app --host 0.0.0.0 --port 8000

엔드포인트:
    POST /synthesize   body: {"text": "나레이션 텍스트"}
                       response: audio/mpeg (MP3 bytes)
    GET  /health       서버 상태 확인
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from tts_server.model import load_model, synthesize


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(title="TTS Server", lifespan=lifespan)


class SynthesizeRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/synthesize")
def synthesize_endpoint(req: SynthesizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")
    try:
        mp3_bytes = synthesize(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(content=mp3_bytes, media_type="audio/mpeg")
