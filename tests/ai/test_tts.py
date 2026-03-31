"""services/ai/tts 유닛 테스트."""
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_tts_mock(audio_bytes: bytes = b"fake_audio_data"):
    response = MagicMock()
    response.content = audio_bytes
    client = MagicMock()
    client.audio.speech.create.return_value = response
    return client


class TestTextToSpeech:
    def test_saves_file(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_client = _make_tts_mock(b"audio_bytes_here")

        with patch("services.ai.tts.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.tts import text_to_speech
            result = text_to_speech("테스트 나레이션", save_path)

        assert result == save_path
        assert Path(save_path).exists()
        assert Path(save_path).read_bytes() == b"audio_bytes_here"

    def test_calls_api_with_correct_params(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_client = _make_tts_mock()

        with patch("services.ai.tts.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.tts import text_to_speech
            text_to_speech("안녕하세요", save_path)

        call_kwargs = mock_client.audio.speech.create.call_args[1]
        assert call_kwargs["model"] == "tts-1"
        assert call_kwargs["voice"] == "nova"
        assert call_kwargs["input"] == "안녕하세요"

    def test_returns_save_path(self, tmp_path):
        save_path = str(tmp_path / "narr.mp3")
        mock_client = _make_tts_mock()

        with patch("services.ai.tts.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.tts import text_to_speech
            result = text_to_speech("텍스트", save_path)

        assert result == save_path
