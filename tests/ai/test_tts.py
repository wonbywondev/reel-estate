"""services/ai/tts 유닛 테스트."""
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_http_mock(content: bytes = b"fake_mp3", status_code: int = 200):
    resp = MagicMock()
    resp.content = content
    resp.ok = status_code < 400
    resp.status_code = status_code
    resp.text = "error" if status_code >= 400 else ""
    return resp


class TestTextToSpeech:
    def test_saves_file(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_resp = _make_http_mock(b"mp3_bytes")

        with patch("services.ai.tts.requests.post", return_value=mock_resp):
            from services.ai.tts import text_to_speech
            result = text_to_speech("테스트 나레이션", save_path)

        assert result == save_path
        assert Path(save_path).exists()
        assert Path(save_path).read_bytes() == b"mp3_bytes"

    def test_posts_to_synthesize_endpoint(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_resp = _make_http_mock()

        with patch("services.ai.tts.requests.post", return_value=mock_resp) as mock_post:
            from services.ai.tts import text_to_speech
            text_to_speech("안녕하세요", save_path)

        call_args = mock_post.call_args
        assert "/synthesize" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "안녕하세요"

    def test_raises_on_server_error(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_resp = _make_http_mock(status_code=500)

        import pytest
        with patch("services.ai.tts.requests.post", return_value=mock_resp):
            from services.ai.tts import text_to_speech
            with pytest.raises(RuntimeError, match="TTS 서버 오류"):
                text_to_speech("텍스트", save_path)

    def test_returns_save_path(self, tmp_path):
        save_path = str(tmp_path / "narr.mp3")
        mock_resp = _make_http_mock()

        with patch("services.ai.tts.requests.post", return_value=mock_resp):
            from services.ai.tts import text_to_speech
            result = text_to_speech("텍스트", save_path)

        assert result == save_path

    def test_uses_env_server_url(self, tmp_path):
        save_path = str(tmp_path / "test.mp3")
        mock_resp = _make_http_mock()

        with patch("services.ai.tts.requests.post", return_value=mock_resp) as mock_post, \
             patch.dict("os.environ", {"TTS_SERVER_URL": "http://my-server:9000"}):
            import importlib
            import services.ai.tts as tts_module
            importlib.reload(tts_module)
            tts_module.text_to_speech("텍스트", save_path)

        assert "my-server:9000" in mock_post.call_args[0][0]
