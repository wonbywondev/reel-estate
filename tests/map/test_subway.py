from unittest.mock import patch, Mock
from services.map.subway import find_nearest_subway


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_find_nearest_subway_returns_station_and_minutes():
    mock_search = Mock()
    mock_search.json.return_value = {
        "items": [
            {"title": "강남역", "mapx": "1270276368", "mapy": "374979507"},
            {"title": "역삼역", "mapx": "1270348000", "mapy": "374982000"},
        ]
    }
    mock_search.raise_for_status = Mock()

    with patch("services.map.subway.requests.get") as mock_get:
        mock_get.side_effect = [
            mock_search,
            Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 400, "duration": 300000}}]}}, raise_for_status=Mock()),
            Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 800, "duration": 600000}}]}}, raise_for_status=Mock()),
        ]
        result = find_nearest_subway(lat=37.4979507, lng=127.0276368)

    assert result["station"] == "강남역"
    assert result["walk_min"] == 5  # 300000ms = 5분


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_find_nearest_subway_raises_when_no_station():
    mock_search = Mock()
    mock_search.json.return_value = {"items": []}
    mock_search.raise_for_status = Mock()

    with patch("services.map.subway.requests.get", return_value=mock_search):
        try:
            find_nearest_subway(lat=37.0, lng=127.0)
            assert False, "Should have raised"
        except ValueError as e:
            assert "지하철역" in str(e)
