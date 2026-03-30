from unittest.mock import patch, Mock
from services.map.geocoding import geocode


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_geocode_returns_lat_lng():
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "addresses": [{"x": "127.0276368", "y": "37.4979507"}],
    }
    mock_response.raise_for_status = Mock()

    with patch("services.map.geocoding.requests.get", return_value=mock_response):
        lat, lng = geocode("서울특별시 강남구 테헤란로 123")

    assert abs(lat - 37.4979507) < 0.0001
    assert abs(lng - 127.0276368) < 0.0001


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_geocode_raises_on_no_result():
    mock_response = Mock()
    mock_response.json.return_value = {"status": "OK", "addresses": []}
    mock_response.raise_for_status = Mock()

    with patch("services.map.geocoding.requests.get", return_value=mock_response):
        try:
            geocode("존재하지않는주소12345")
            assert False, "Should have raised"
        except ValueError as e:
            assert "주소를 찾을 수 없습니다" in str(e)
