"""services/street/playwright_shot 유닛 테스트.

실제 브라우저 없이 Playwright 내부를 mock해서 로직만 검증한다.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper: Playwright mock hierarchy
# ---------------------------------------------------------------------------

def _make_playwright_mock(url_after_click: str = "https://map.naver.com/p?c=17,0,0,0,dh&p=PANO123,0,0,0,Float"):
    """sync_playwright() context manager mock을 만든다."""
    page = MagicMock()
    page.url = url_after_click

    browser = MagicMock()
    browser.new_page.return_value = page

    chromium = MagicMock()
    chromium.launch.return_value = browser

    pw = MagicMock()
    pw.chromium = chromium

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=pw)
    ctx.__exit__ = MagicMock(return_value=False)

    return ctx, page, browser


# ---------------------------------------------------------------------------
# _get_pano_id
# ---------------------------------------------------------------------------

class TestGetPanoId:
    def test_extracts_pano_id_from_url(self):
        ctx, page, _ = _make_playwright_mock(
            url_after_click="https://map.naver.com/p?c=17,0,0,0&p=PANO_ABC,0,0,0,Float"
        )
        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _get_pano_id
            result = _get_pano_id(37.49, 127.02)
        assert result == "PANO_ABC"

    def test_returns_none_when_no_pano_id(self):
        ctx, page, _ = _make_playwright_mock(
            url_after_click="https://map.naver.com/p?c=17,0,0,0,dh"
        )
        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _get_pano_id
            result = _get_pano_id(37.49, 127.02)
        assert result is None

    def test_skips_popup_click_when_not_found(self):
        """popup이 없을 때(None 반환) click을 호출하지 않아 예외가 발생하지 않는다."""
        ctx, page, _ = _make_playwright_mock()
        page.query_selector.return_value = None  # popup 없음

        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _get_pano_id
            # None이 반환될 때 click을 시도하면 AttributeError → 정상 처리되어야 함
            _get_pano_id(37.49, 127.02)  # 예외 없이 완료되면 OK

        page.query_selector.assert_called()

    def test_navigates_to_correct_url(self):
        ctx, page, _ = _make_playwright_mock()
        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _get_pano_id
            _get_pano_id(37.49, 127.02)

        first_goto = page.goto.call_args_list[0]
        assert "127.02" in first_goto[0][0]
        assert "37.49" in first_goto[0][0]


# ---------------------------------------------------------------------------
# _capture_street_view
# ---------------------------------------------------------------------------

class TestCaptureStreetView:
    def test_saves_screenshot(self, tmp_path):
        save_path = str(tmp_path / "sv.png")
        ctx, page, _ = _make_playwright_mock()
        page.query_selector.return_value = MagicMock()  # onboarding btn

        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _capture_street_view
            result = _capture_street_view("PANO123", save_path)

        assert result == save_path
        page.screenshot.assert_called_once_with(path=save_path)

    def test_url_contains_pano_id(self):
        ctx, page, _ = _make_playwright_mock()
        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _capture_street_view
            _capture_street_view("MY_PANO_ID", "/tmp/x.png")

        goto_url = page.goto.call_args[0][0]
        assert "MY_PANO_ID" in goto_url

    def test_hides_dialogs_via_js(self):
        """팝업 숨김을 JS evaluate로 처리한다."""
        ctx, page, _ = _make_playwright_mock()

        with patch("services.street.playwright_shot.sync_playwright", return_value=ctx):
            from services.street.playwright_shot import _capture_street_view
            _capture_street_view("PANO123", "/tmp/x.png")

        # evaluate가 dialog 숨기는 JS로 호출됐는지 확인
        eval_calls = [str(c) for c in page.evaluate.call_args_list]
        assert any("dialog" in c for c in eval_calls)


# ---------------------------------------------------------------------------
# _fallback_satellite
# ---------------------------------------------------------------------------

FAKE_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00\x01'
    b'\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82'
)


class TestFallbackSatellite:
    def test_saves_satellite_image(self, tmp_path):
        save_path = str(tmp_path / "satellite.png")
        mock_resp = MagicMock()
        mock_resp.content = FAKE_PNG
        mock_resp.raise_for_status = MagicMock()

        with patch("services.street.playwright_shot.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}):
            from services.street.playwright_shot import _fallback_satellite
            result = _fallback_satellite(37.49, 127.02, save_path)

        assert result == save_path
        assert Path(save_path).read_bytes() == FAKE_PNG

    def test_uses_satellite_maptype(self):
        mock_resp = MagicMock()
        mock_resp.content = FAKE_PNG
        mock_resp.raise_for_status = MagicMock()

        with patch("services.street.playwright_shot.requests.get", return_value=mock_resp) as mock_get, \
             patch.dict("os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}):
            from services.street.playwright_shot import _fallback_satellite
            _fallback_satellite(37.49, 127.02, "/tmp/sat.png")

        params = mock_get.call_args[1]["params"]
        assert params.get("maptype") == "satellite"


# ---------------------------------------------------------------------------
# take_street_view (통합 시나리오)
# ---------------------------------------------------------------------------

class TestTakeStreetView:
    def test_returns_street_view_when_pano_found(self, tmp_path):
        save_path = str(tmp_path / "sv.png")
        with patch("services.street.playwright_shot._get_pano_id", return_value="PANO_XYZ"), \
             patch("services.street.playwright_shot._capture_street_view", return_value=save_path) as mock_cap:
            from services.street.playwright_shot import take_street_view
            result = take_street_view(37.49, 127.02, save_path)

        mock_cap.assert_called_once_with("PANO_XYZ", save_path)
        assert result == save_path

    def test_falls_back_when_pano_is_none(self, tmp_path):
        save_path = str(tmp_path / "sat.png")
        with patch("services.street.playwright_shot._get_pano_id", return_value=None), \
             patch("services.street.playwright_shot._fallback_satellite", return_value=save_path) as mock_fb:
            from services.street.playwright_shot import take_street_view
            result = take_street_view(37.49, 127.02, save_path)

        mock_fb.assert_called_once_with(37.49, 127.02, save_path)
        assert result == save_path

    def test_falls_back_when_get_pano_raises(self, tmp_path):
        save_path = str(tmp_path / "sat.png")
        with patch("services.street.playwright_shot._get_pano_id", side_effect=Exception("timeout")), \
             patch("services.street.playwright_shot._fallback_satellite", return_value=save_path) as mock_fb:
            from services.street.playwright_shot import take_street_view
            result = take_street_view(37.49, 127.02, save_path)

        mock_fb.assert_called_once()
        assert result == save_path

    def test_falls_back_when_capture_raises(self, tmp_path):
        save_path = str(tmp_path / "sat.png")
        with patch("services.street.playwright_shot._get_pano_id", return_value="PANO_XYZ"), \
             patch("services.street.playwright_shot._capture_street_view", side_effect=Exception("render fail")), \
             patch("services.street.playwright_shot._fallback_satellite", return_value=save_path) as mock_fb:
            from services.street.playwright_shot import take_street_view
            result = take_street_view(37.49, 127.02, save_path)

        mock_fb.assert_called_once()
        assert result == save_path
