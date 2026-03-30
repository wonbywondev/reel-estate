from unittest.mock import patch, Mock
from services.map.subway import find_nearby_subways
from services.map.subway.station_db import Station


MOCK_STATIONS = [
    Station(name="강남역", line="2호선", lat=37.4979507, lng=127.0276368),
    Station(name="역삼역", line="2호선", lat=37.4982000, lng=127.0348000),
    Station(name="신논현역", line="9호선", lat=37.5050000, lng=127.0250000),
]


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_find_nearby_subways_returns_sorted_within_cutoff():
    # 강남역 400m/5분, 역삼역 800m/10분(같은 2호선 제외), 신논현역 750m/9분(9호선 포함)
    with patch("services.map.subway.finder.find_nearby_stations", return_value=MOCK_STATIONS), \
         patch("services.map.subway.finder.requests.get") as mock_get:
        mock_get.side_effect = [
            Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 400, "duration": 300000}}]}}, raise_for_status=Mock()),
            Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 800, "duration": 600000}}]}}, raise_for_status=Mock()),
            Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 750, "duration": 540000}}]}}, raise_for_status=Mock()),
        ]
        result = find_nearby_subways(lat=37.4979507, lng=127.0276368)

    assert result[0]["station"] == "강남역 2호선"
    assert result[0]["walk_min"] == 5
    # 역삼역은 같은 2호선이므로 제외, 신논현역(9호선)은 포함
    lines = [r["station"].split()[-1] for r in result]
    assert "2호선" in lines
    assert "9호선" in lines


@patch.dict("os.environ", {"NAVER_CLIENT_ID": "test_id", "NAVER_CLIENT_SECRET": "test_secret"})
def test_find_nearby_subways_raises_when_no_station():
    with patch("services.map.subway.finder.find_nearby_stations", return_value=[]):
        try:
            find_nearby_subways(lat=37.0, lng=127.0)
            assert False, "Should have raised"
        except ValueError as e:
            assert "지하철역" in str(e)
