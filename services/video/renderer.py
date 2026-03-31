"""슬라이드 이미지를 MoviePy로 MP4 영상으로 렌더링한다."""
import numpy as np
from pathlib import Path
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips
from moviepy.video.VideoClip import VideoClip

# 오디오 없는 슬라이드의 기본 지속 시간(초)
DEFAULT_DURATION = 3.0


def render_video(
    slides: list[tuple[Image.Image, float, str | None]],
    save_path: str,
) -> str:
    """슬라이드 이미지 목록을 MP4로 렌더링한다.

    Args:
        slides: [(PIL.Image, 기본초, 오디오경로 or None)] 리스트
                오디오가 있으면 오디오 길이로 duration 결정, 없으면 기본초 사용
        save_path: 저장 경로 (.mp4)

    Returns:
        저장된 파일 경로
    """
    clips = []
    audio_clips = []
    has_audio = any(audio_path for _, _, audio_path in slides)

    for img, default_duration, audio_path in slides:
        arr = np.array(img.convert("RGB"))

        if audio_path and Path(audio_path).exists():
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio_clips.append(audio)
        else:
            duration = default_duration
            if has_audio:
                # 다른 슬라이드에 오디오가 있으면 무음 오디오로 맞춤
                audio_clips.append(None)

        clips.append(ImageClip(arr, duration=duration))

    video: VideoClip = concatenate_videoclips(clips, method="compose")  # type: ignore[assignment]

    if has_audio:
        # None 슬라이드는 해당 duration만큼 무음으로 채움
        final_audios = []
        for i, (_, _, _) in enumerate(slides):
            if audio_clips[i] is not None:
                final_audios.append(audio_clips[i])
            else:
                # 무음 대체: 해당 클립 duration만큼 silence
                from moviepy.audio.AudioClip import AudioClip as MpAudioClip
                silence = MpAudioClip(
                    lambda t: [0, 0],
                    duration=clips[i].duration,
                    fps=44100,
                )
                final_audios.append(silence)

        combined_audio = concatenate_audioclips(final_audios)  # type: ignore[arg-type]
        video = video.with_audio(combined_audio)

    video.write_videofile(
        save_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    return save_path
