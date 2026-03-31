"""OpenAI로 부동산 릴스용 대본(나레이션), 광고 카피, 해시태그를 생성한다."""
import os
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-5-mini"

SYSTEM_PROMPT = """당신은 인스타그램 릴스용 부동산 광고 카피라이터입니다.
공인중개사가 제공한 매물 정보를 바탕으로 20~30대 직장인을 타겟으로 한 짧고 임팩트 있는 카피와 나레이션 대본을 작성합니다.
반드시 JSON 형식으로만 응답하세요."""

COPY_PROMPT = """다음 매물 정보로 인스타그램 릴스 광고 카피와 슬라이드별 나레이션 대본을 작성해주세요.

매물 정보:
- 주소: {address}
- 가격: {price_str}
- 평수: {size_pyeong}평
- 층수: {floor}층
- 준공연도: {year_built}년
- 전세 대출 가능: {loan_str}
- 옵션: {options_str}
- 가까운 지하철: {subway_str}
- 중개자 코멘트: {comment_str}
- 실내 사진 수: {interior_count}장

슬라이드 구성 ({slide_count}개):
{slide_list}

다음 JSON 형식으로만 응답하세요:
{{
  "narrations": ["슬라이드1 나레이션", "슬라이드2 나레이션", ...],
  "features": ["특징 1 (15자 이내)", "특징 2 (15자 이내)", "특징 3 (15자 이내)"],
  "cta": "행동 유도 문구 (15자 이내, 예: DM 주세요 / 지금 문의하세요)",
  "hashtags": ["해시태그1", "해시태그2", "해시태그3", "해시태그4", "해시태그5"]
}}

나레이션 작성 규칙:
- 각 나레이션은 20~35자 이내의 자연스러운 구어체
- TTS로 읽힐 문장이므로 특수기호 사용 금지
- 슬라이드 내용에 맞는 자연스러운 흐름"""


def generate_copy(
    address: str,
    floor: int,
    size_pyeong: float,
    deposit: int,
    monthly_rent: int,
    options: list[str],
    year_built: int,
    subway_list: list[dict],
    loan_available: bool = False,
    agent_comment: str | None = None,
    interior_count: int = 0,
) -> dict:
    """매물 정보로 나레이션 대본, 광고 카피, 해시태그를 생성한다.

    Returns:
        {
            "narrations": ["슬라이드별 나레이션..."],
            "features": ["특징1", "특징2", "특징3"],
            "cta": "행동 유도 문구",
            "hashtags": ["해시태그1", ...]
        }
    """
    price_str = _format_price(deposit, monthly_rent)
    options_str = ", ".join(options) if options else "없음"
    subway_str = _format_subway(subway_list)
    loan_str = "가능" if loan_available else "불가"
    comment_str = agent_comment if agent_comment else "없음"

    # 슬라이드 구성 목록 생성
    slides = ["지도 (주변 지하철역)", "거리뷰 (주변 환경)"]
    for i in range(interior_count):
        slides.append(f"실내 사진 {i + 1}")
    slides += ["방 정보 카드 (가격/옵션)", "특징 3가지", "CTA"]

    slide_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slides))

    prompt = COPY_PROMPT.format(
        address=address,
        price_str=price_str,
        size_pyeong=size_pyeong,
        floor=floor,
        year_built=year_built,
        loan_str=loan_str,
        options_str=options_str,
        subway_str=subway_str,
        comment_str=comment_str,
        interior_count=interior_count,
        slide_count=len(slides),
        slide_list=slide_list,
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
