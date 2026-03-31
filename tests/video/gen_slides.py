"""슬라이드 이미지 + 대본 생성 테스트 스크립트.

실제 API를 호출하여 슬라이드 이미지를 output/{slug}_{timestamp}/ 폴더에 저장한다.
영상 렌더링 없이 이미지만 확인하는 용도.

사용법:
    uv run python tests/video/gen_slides.py
"""
import sys
import datetime
import json
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from services.map.geocoding import geocode
from services.map.subway import find_nearby_subways
from services.map.static_map import download_static_map, download_static_map_wide
from services.map.nearby import find_nearby_shops
from services.street.playwright_shot import take_street_view
from services.ai.copy_writer import generate_copy
from services.video.templates import (
    slide_title, slide_map, slide_street, slide_interior,
    slide_room_info, slide_nearby_shops, slide_copy, slide_cta,
)

# ---------------------------------------------------------------------------
# 테스트 매물 정보
# ---------------------------------------------------------------------------

ADDRESS = "인천 연수구 인천타워대로 253-25"
FLOOR = 5
SIZE_PYEONG = 12.0
DEPOSIT = 2000
MONTHLY_RENT = 70
OPTIONS = ["에어컨", "세탁기", "냉장고", "인터넷"]
YEAR_BUILT = 2018
LOAN_AVAILABLE = True
AGENT_COMMENT = "인천타워 인근 역세권 매물입니다."
INTERIOR_PATHS: list[str] = []  # 실내 사진 없음

# ---------------------------------------------------------------------------
# 출력 폴더 생성
# ---------------------------------------------------------------------------

slug = ADDRESS[:10].replace(" ", "_")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = Path("output") / f"{slug}_{timestamp}"
out_dir.mkdir(parents=True, exist_ok=True)
print(f"\n[출력 폴더] {out_dir}\n")


def step(msg: str):
    print(f"▶ {msg}")


# ---------------------------------------------------------------------------
# 1. 좌표 변환
# ---------------------------------------------------------------------------

step("주소 좌표 변환")
lat, lng = geocode(ADDRESS)
print(f"  → {lat}, {lng}")

# ---------------------------------------------------------------------------
# 2. 지하철
# ---------------------------------------------------------------------------

step("주변 지하철역 검색")
subway_list = find_nearby_subways(lat, lng)
for s in subway_list:
    print(f"  → {s['station']} 도보 {s['walk_min']}분")

# ---------------------------------------------------------------------------
# 3. 지도 이미지
# ---------------------------------------------------------------------------

step("넓은 지도 다운로드")
wide_map_path = str(out_dir / "map_wide.png")
download_static_map_wide(lat, lng, wide_map_path)
print(f"  → {wide_map_path}")

step("좁은 지도 다운로드")
map_path = str(out_dir / "map.png")
download_static_map(lat, lng, subway_list, map_path)
print(f"  → {map_path}")

# ---------------------------------------------------------------------------
# 4. 편의시설
# ---------------------------------------------------------------------------

step("근처 편의시설 검색")
region_hint = " ".join(ADDRESS.split()[:2])  # "인천 연수구"
shops_list = find_nearby_shops(lat, lng, region_hint=region_hint)
for s in shops_list:
    print(f"  → {s['name']} ({s['distance']}m)")

# ---------------------------------------------------------------------------
# 5. 거리뷰
# ---------------------------------------------------------------------------

step("거리뷰 캡처")
sv_path = str(out_dir / "streetview.png")
take_street_view(lat, lng, sv_path)
print(f"  → {sv_path}")

# ---------------------------------------------------------------------------
# 6. AI 카피 + 나레이션
# ---------------------------------------------------------------------------

step("AI 대본 생성")
copy = generate_copy(
    address=ADDRESS,
    floor=FLOOR,
    size_pyeong=SIZE_PYEONG,
    deposit=DEPOSIT,
    monthly_rent=MONTHLY_RENT,
    options=OPTIONS,
    year_built=YEAR_BUILT,
    subway_list=subway_list,
    loan_available=LOAN_AVAILABLE,
    agent_comment=AGENT_COMMENT,
    interior_count=len(INTERIOR_PATHS),
)
narrations: list[str] = copy.get("narrations", [])

# ---------------------------------------------------------------------------
# 7. 슬라이드 이미지 저장 (자막 포함)
# ---------------------------------------------------------------------------

step("슬라이드 이미지 저장")

def _narr(idx: int) -> str:
    return narrations[idx] if idx < len(narrations) else ""

parts = ADDRESS.split()
neighborhood = " ".join(parts[1:3]) if len(parts) >= 3 else parts[0]

slides_meta: list[tuple[str, str]] = []  # (파일명, 나레이션)
n = 0

def save_slide(name: str, img, narration: str):
    path = out_dir / name
    img.save(path)
    slides_meta.append((name, narration))
    print(f"  → {name}")

save_slide(f"{n+1:02d}_title.png", slide_title(neighborhood, subtitle=_narr(n)), _narr(n))
n += 1
save_slide(f"{n+1:02d}_map_wide.png", slide_map(wide_map_path, subtitle=_narr(n)), _narr(n))
n += 1
save_slide(f"{n+1:02d}_map.png", slide_map(map_path, subtitle=_narr(n)), _narr(n))
n += 1
save_slide(f"{n+1:02d}_streetview.png", slide_street(sv_path, subtitle=_narr(n)), _narr(n))
n += 1
for i, ipath in enumerate(INTERIOR_PATHS):
    save_slide(f"{n+1:02d}_interior_{i+1}.png", slide_interior(ipath, subtitle=_narr(n)), _narr(n))
    n += 1
save_slide(f"{n+1:02d}_room_info.png", slide_room_info(
    address=ADDRESS, floor=FLOOR, size_pyeong=SIZE_PYEONG,
    deposit=DEPOSIT, monthly_rent=MONTHLY_RENT, year_built=YEAR_BUILT,
    options=OPTIONS, loan_available=LOAN_AVAILABLE, subtitle=_narr(n),
), _narr(n))
n += 1
save_slide(f"{n+1:02d}_shops.png", slide_nearby_shops(shops_list, subtitle=_narr(n)), _narr(n))
n += 1
save_slide(f"{n+1:02d}_copy.png", slide_copy(copy["features"], subtitle=_narr(n)), _narr(n))
n += 1
save_slide(f"{n+1:02d}_cta.png", slide_cta(copy["cta"], copy["hashtags"], subtitle=_narr(n)), _narr(n))

# ---------------------------------------------------------------------------
# 9. 대본 저장
# ---------------------------------------------------------------------------

step("대본 저장")
script_path = out_dir / "script.txt"
with open(script_path, "w", encoding="utf-8") as f:
    for filename, narration in slides_meta:
        f.write(f"[{filename}]\n{narration}\n\n")

    f.write("---\n\n")
    f.write("[특징]\n")
    for feat in copy["features"]:
        f.write(f"- {feat}\n")
    f.write(f"\n[CTA]\n{copy['cta']}\n\n")
    f.write(f"[해시태그]\n{' '.join(copy['hashtags'])}\n")

print(f"  → script.txt")

# ---------------------------------------------------------------------------
# 10. 메타데이터 저장
# ---------------------------------------------------------------------------

meta = {
    "address": ADDRESS,
    "lat": lat, "lng": lng,
    "subway": subway_list,
    "shops": shops_list,
    "copy": copy,
}
with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n✅ 완료: {out_dir}")
print(f"   슬라이드 {len(slides_meta)}장")
