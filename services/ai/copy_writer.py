"""OpenAI로 부동산 릴스용 대본(나레이션), 광고 카피, 해시태그를 생성한다."""
import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from services.ai.prompts import SYSTEM_PROMPT, COPY_PROMPT

load_dotenv()

MODEL = "gpt-5-mini"


def build_slide_list(
    interior_count: int = 0,
    interior_labels: list[str] | None = None,
    shop_categories: list[str] | None = None,
) -> list[str]:
    """실제 렌더링 순서와 동일한 슬라이드 목록을 반환한다."""
    slides = [
        "썸네일 (주소 + 가격)",
        "넓은 지도 (동네 위치)",
        "거리뷰 (주변 환경 묘사)",
    ]
    for i in range(interior_count):
        lbl = (interior_labels or [])[i] if interior_labels and i < len(interior_labels) else ""
        slides.append(f"실내 사진 {i + 1}" + (f" ({lbl})" if lbl else ""))
    slides.append("지하철역 지도 (역명 + 도보 거리)")
    for cat in (shop_categories or []):
        slides.append(f"근처 편의시설 — {cat}")
    slides.append("방 정보 (평수/층/준공/방향/방구성/옵션)")
    slides.append("가격 (보증금/월세/전세대출)")
    slides.append("CTA (문의 유도)")
    return slides


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
    interior_labels: list[str] | None = None,
    shop_categories: list[str] | None = None,
) -> dict:
    """매물 정보로 나레이션 대본, 광고 카피, 해시태그를 생성한다.

    Returns:
        {
            "narrations": ["슬라이드별 나레이션..."],
            "cta": "행동 유도 문구",
            "hashtags": ["해시태그1", ...]
        }
    """
    price_str = _format_price(deposit, monthly_rent)
    options_str = ", ".join(options) if options else "없음"
    subway_str = _format_subway(subway_list)
    loan_str = "가능" if loan_available else "불가"
    comment_str = agent_comment if agent_comment else "없음"

    slides = build_slide_list(interior_count, interior_labels, shop_categories)
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
