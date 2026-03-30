"""슬라이드 이미지를 MoviePy로 MP4 영상으로 렌더링한다."""
import numpy as np
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.VideoClip import VideoClip


def render_video(
    slides: list[tuple[Image.Image, float]],
    save_path: str,
    bgm_path: str | None = None,
) -> str:
    """슬라이드 이미지 목록을 MP4로 렌더링한다.

    Args:
        slides: [(PIL.Image, 초)] 리스트
        save_path: 저장 경로 (.mp4)
        bgm_path: BGM 파일 경로 (없으면 무음)

    Returns:
        저장된 파일 경로
    """
    clips = []
    for img, duration in slides:
        arr = np.array(img.convert("RGB"))
        clip = ImageClip(arr, duration=duration)
        clips.append(clip)

    video: VideoClip = concatenate_videoclips(clips, method="compose")  # type: ignore[assignment]

    if bgm_path:
        try:
            audio = AudioFileClip(bgm_path).with_duration(video.duration)
            video = video.with_audio(audio)
        except Exception:
            pass

    video.write_videofile(
        save_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    return save_path
