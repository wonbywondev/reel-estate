"""OpenAI로 부동산 릴스용 광고 카피와 해시태그를 생성한다."""
import os
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-5-mini"

SYSTEM_PROMPT = """당신은 인스타그램 릴스용 부동산 광고 카피라이터입니다.
공인중개사가 제공한 매물 정보를 바탕으로 20~30대 직장인을 타겟으로 한 짧고 임팩트 있는 카피를 작성합니다.
반드시 JSON 형식으로만 응답하세요."""

COPY_PROMPT = """다음 매물 정보로 인스타그램 릴스 광고 카피를 작성해주세요.

매물 정보:
- 주소: {address}
- 가격: {price_str}
- 평수: {size_pyeong}평
- 층수: {floor}층
- 준공연도: {year_built}년
- 옵션: {options_str}
- 가까운 지하철: {subway_str}

다음 JSON 형식으로만 응답하세요:
{{
  "hook": "첫 1~2초 시선을 끄는 후크 문장 (20자 이내, 물음표나 감탄사 활용)",
  "features": ["특징 1 (15자 이내)", "특징 2 (15자 이내)", "특징 3 (15자 이내)"],
  "cta": "행동 유도 문구 (15자 이내, 예: DM 주세요 / 지금 문의하세요)",
  "hashtags": ["해시태그1", "해시태그2", "해시태그3", "해시태그4", "해시태그5"]
}}"""


def generate_copy(
    address: str,
    floor: int,
    size_pyeong: float,
    deposit: int,
    monthly_rent: int,
    options: list[str],
    year_built: int,
    subway_list: list[dict],
) -> dict:
    """매물 정보로 광고 카피와 해시태그를 생성한다.

    Returns:
        {
            "hook": "후크 문장",
            "features": ["특징1", "특징2", "특징3"],
            "cta": "행동 유도 문구",
            "hashtags": ["해시태그1", ...]
        }
    """
    price_str = _format_price(deposit, monthly_rent)
    options_str = ", ".join(options) if options else "없음"
    subway_str = _format_subway(subway_list)

    prompt = COPY_PROMPT.format(
        address=address,
        price_str=price_str,
        size_pyeong=size_pyeong,
        floor=floor,
        year_built=year_built,
        options_str=options_str,
        subway_str=subway_str,
    )

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or ""
    return json.loads(raw)


def _format_price(deposit: int, monthly_rent: int) -> str:
    if monthly_rent == 0:
        return f"전세 {deposit:,}만원"
    return f"보증금 {deposit:,}만원 / 월세 {monthly_rent:,}만원"


def _format_subway(subway_list: list[dict]) -> str:
    if not subway_list:
        return "정보 없음"
    parts = [f"{s['station']} 도보 {s['walk_min']}분" for s in subway_list]
    return ", ".join(parts)
