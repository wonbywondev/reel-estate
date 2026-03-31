"""services/map/nearby 유닛 테스트."""
from unittest.mock import MagicMock, patch


def _make_search_mock(items: list[dict]):
    resp = MagicMock()
    resp.json.return_value = {"items": items}
    resp.raise_for_status = MagicMock()
    return resp


MOCK_ITEMS = [
    {
        "title": "강남<b>마트</b>",
        "category": "대형마트",
        "roadAddress": "서울시 강남구 역삼동 1",
        "mapx": "1270497580",  # 127.049758 * 1e7
        "mapy": "374977000",   # 37.4977 * 1e7
    },
    {
        "title": "역삼 슈퍼",
        "category": "슈퍼마켓",
        "roadAddress": "서울시 강남구 역삼동 2",
        "mapx": "1270500000",
        "mapy": "374980000",
    },
]

# 매물 좌표 (강남 근처)
LAT, LNG = 37.4975, 127.0500


class TestFindNearbyShops:
    def test_returns_list(self):
        mock_resp = _make_search_mock(MOCK_ITEMS)
        with patch("services.map.nearby.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        assert isinstance(result, list)

    def test_result_has_required_keys(self):
        mock_resp = _make_search_mock(MOCK_ITEMS)
        with patch("services.map.nearby.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        for item in result:
            assert "name" in item
            assert "category" in item
            assert "distance" in item

    def test_strips_html_tags(self):
        mock_resp = _make_search_mock(MOCK_ITEMS)
        with patch("services.map.nearby.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        names = [item["name"] for item in result]
        for name in names:
            assert "<b>" not in name
            assert "</b>" not in name

    def test_max_five_results(self):
        many_items = [
            {
                "title": f"마트{i}",
                "category": "대형마트",
                "mapx": str(int((LNG + i * 0.0001) * 1e7)),
                "mapy": str(int((LAT + i * 0.0001) * 1e7)),
            }
            for i in range(10)
        ]
        mock_resp = _make_search_mock(many_items)
        with patch("services.map.nearby.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        assert len(result) <= 5

    def test_returns_empty_on_api_error(self):
        with patch("services.map.nearby.requests.get", side_effect=Exception("network error")), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        assert result == []

    def test_sorted_by_distance(self):
        # 더 가까운 항목이 먼저 와야 함
        items = [
            {
                "title": "먼마트",
                "category": "대형마트",
                "mapx": str(int((LNG + 0.005) * 1e7)),  # 더 먼 곳
                "mapy": str(int(LAT * 1e7)),
            },
            {
                "title": "가까운마트",
                "category": "대형마트",
                "mapx": str(int((LNG + 0.001) * 1e7)),  # 더 가까운 곳
                "mapy": str(int(LAT * 1e7)),
            },
        ]
        mock_resp = _make_search_mock(items)
        with patch("services.map.nearby.requests.get", return_value=mock_resp), \
             patch.dict("os.environ", {
                 "NAVER_SEARCH_CLIENT_ID": "test",
                 "NAVER_SEARCH_CLIENT_SECRET": "test",
                 "NAVER_CLIENT_ID": "test",
                 "NAVER_CLIENT_SECRET": "test",
             }):
            from services.map.nearby import find_nearby_shops
            result = find_nearby_shops(LAT, LNG)

        if len(result) >= 2:
            assert result[0]["distance"] <= result[1]["distance"]


class TestStripTags:
    def test_removes_bold_tags(self):
        from services.map.nearby import _strip_tags
        assert _strip_tags("강남<b>마트</b>") == "강남마트"

    def test_no_tags_unchanged(self):
        from services.map.nearby import _strip_tags
        assert _strip_tags("강남마트") == "강남마트"
