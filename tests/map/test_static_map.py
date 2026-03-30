from unittest.mock import patch, Mock
from services.map.static_map import download_static_map


def test_download_static_map_saves_file(tmp_path):
    # 1x1 투명 PNG (최소 유효 PNG 바이트)
    fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82'
    mock_resp = Mock()
    mock_resp.content = fake_png
    mock_resp.raise_for_status = Mock()

    output_path = tmp_path / "map.png"
    with patch("services.map.static_map.requests.get", return_value=mock_resp), \
         patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"}):
        result = download_static_map(
            lat=37.4979507, lng=127.0276368,
            subway_info={"station": "강남역", "walk_min": 5},
            save_path=str(output_path),
        )

    assert result == str(output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_download_static_map_uses_correct_params():
    fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82'
    mock_resp = Mock()
    mock_resp.content = fake_png
    mock_resp.raise_for_status = Mock()

    with patch("services.map.static_map.requests.get", return_value=mock_resp) as mock_get, \
         patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"}):
        download_static_map(
            lat=37.4979507, lng=127.0276368,
            subway_info={"station": "강남역", "walk_min": 5},
            save_path="/tmp/test_map.png",
        )
        call_params = mock_get.call_args[1]["params"]
        assert "127.0276368" in call_params["center"]
        assert call_params["w"] == 1080
        assert call_params["h"] == 608
