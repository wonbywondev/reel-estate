"""services/ai/copy_writer 유닛 테스트."""
import json
from unittest.mock import MagicMock, patch

MOCK_RESPONSE = {
    "hook": "월세 50만원에 이 퀄리티?",
    "features": ["강남역 도보 5분", "풀옵션 완비", "신축급 깔끔함"],
    "cta": "DM으로 문의하세요",
    "hashtags": ["강남원룸", "역세권월세", "풀옵션", "강남부동산", "직장인추천"],
}

SUBWAY_LIST = [
    {"station": "강남역 2호선", "walk_min": 5, "walk_m": 400},
    {"station": "신논현역 9호선", "walk_min": 7, "walk_m": 600},
]


def _make_openai_mock(response_dict: dict):
    """OpenAI client.chat.completions.create mock을 만든다."""
    message = MagicMock()
    message.content = json.dumps(response_dict, ensure_ascii=False)

    choice = MagicMock()
    choice.message = message

    completion = MagicMock()
    completion.choices = [choice]

    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


class TestGenerateCopy:
    def test_returns_required_keys(self):
        mock_client = _make_openai_mock(MOCK_RESPONSE)
        with patch("services.ai.copy_writer.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.copy_writer import generate_copy
            result = generate_copy(
                address="서울시 강남구 역삼동 123",
                floor=3, size_pyeong=10.0,
                deposit=1000, monthly_rent=50,
                options=["에어컨", "세탁기"],
                year_built=2020,
                subway_list=SUBWAY_LIST,
            )

        assert "hook" in result
        assert "features" in result
        assert "cta" in result
        assert "hashtags" in result

    def test_features_is_list_of_three(self):
        mock_client = _make_openai_mock(MOCK_RESPONSE)
        with patch("services.ai.copy_writer.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.copy_writer import generate_copy
            result = generate_copy(
                address="서울시 강남구 역삼동 123",
                floor=3, size_pyeong=10.0,
                deposit=1000, monthly_rent=50,
                options=[], year_built=2020,
                subway_list=SUBWAY_LIST,
            )

        assert isinstance(result["features"], list)
        assert len(result["features"]) == 3

    def test_prompt_contains_address_and_price(self):
        mock_client = _make_openai_mock(MOCK_RESPONSE)
        with patch("services.ai.copy_writer.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.copy_writer import generate_copy
            generate_copy(
                address="서울시 강남구 역삼동 123",
                floor=3, size_pyeong=10.0,
                deposit=1000, monthly_rent=50,
                options=[], year_built=2020,
                subway_list=SUBWAY_LIST,
            )

        call_messages = mock_client.chat.completions.create.call_args[1]["messages"]
        user_content = next(m["content"] for m in call_messages if m["role"] == "user")
        assert "서울시 강남구 역삼동 123" in user_content
        assert "1,000만원" in user_content
        assert "50만원" in user_content

    def test_prompt_contains_subway_info(self):
        mock_client = _make_openai_mock(MOCK_RESPONSE)
        with patch("services.ai.copy_writer.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.copy_writer import generate_copy
            generate_copy(
                address="서울시 강남구 역삼동 123",
                floor=3, size_pyeong=10.0,
                deposit=1000, monthly_rent=50,
                options=[], year_built=2020,
                subway_list=SUBWAY_LIST,
            )

        call_messages = mock_client.chat.completions.create.call_args[1]["messages"]
        user_content = next(m["content"] for m in call_messages if m["role"] == "user")
        assert "강남역 2호선" in user_content
        assert "5분" in user_content

    def test_uses_json_response_format(self):
        mock_client = _make_openai_mock(MOCK_RESPONSE)
        with patch("services.ai.copy_writer.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            from services.ai.copy_writer import generate_copy
            generate_copy(
                address="서울시 강남구 역삼동 123",
                floor=3, size_pyeong=10.0,
                deposit=1000, monthly_rent=50,
                options=[], year_built=2020,
                subway_list=[],
            )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}


class TestFormatHelpers:
    def test_format_price_monthly(self):
        from services.ai.copy_writer import _format_price
        assert _format_price(500, 40) == "보증금 500만원 / 월세 40만원"

    def test_format_price_jeonse(self):
        from services.ai.copy_writer import _format_price
        assert _format_price(30000, 0) == "전세 30,000만원"

    def test_format_subway_multiple(self):
        from services.ai.copy_writer import _format_subway
        result = _format_subway(SUBWAY_LIST)
        assert "강남역 2호선 도보 5분" in result
        assert "신논현역 9호선 도보 7분" in result

    def test_format_subway_empty(self):
        from services.ai.copy_writer import _format_subway
        assert _format_subway([]) == "정보 없음"
