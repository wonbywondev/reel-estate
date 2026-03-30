"""부동산 릴스 자동 생성기 — Streamlit 앱."""
from pathlib import Path

import streamlit as st

from db.database import Database
from db.models import Room
from services.map.geocoding import geocode
from services.map.subway import find_nearby_subways
from services.map.static_map import download_static_map
from services.street.playwright_shot import take_street_view
from services.ai.copy_writer import generate_copy

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

OPTIONS_LIST = [
    "에어컨", "세탁기", "냉장고", "전자레인지", "인덕션", "가스레인지",
    "TV", "침대", "옷장", "책상", "신발장", "인터넷", "주차가능", "엘리베이터",
]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# DB 초기화 (세션당 1회)
# ---------------------------------------------------------------------------

if "db" not in st.session_state:
    db = Database()
    db.init()
    st.session_state["db"] = db

db: Database = st.session_state["db"]

# ---------------------------------------------------------------------------
# 레이아웃
# ---------------------------------------------------------------------------

st.set_page_config(page_title="부동산 릴스 생성기", page_icon="🏠", layout="wide")
st.title("🏠 부동산 릴스 자동 생성기")

left, right = st.columns([1, 1], gap="large")

# ---------------------------------------------------------------------------
# 왼쪽: 입력 폼
# ---------------------------------------------------------------------------

with left:
    st.subheader("매물 정보 입력")
    with st.form("room_form"):
        address = st.text_input("도로명 주소 *", placeholder="예: 서울시 강남구 역삼동 123")

        col1, col2 = st.columns(2)
        with col1:
            deposit = st.number_input("보증금 (만원)", min_value=0, value=1000, step=100)
            size_pyeong = st.number_input("평수", min_value=1.0, value=10.0, step=0.5)
            year_built = st.number_input("준공연도", min_value=1970, max_value=2030, value=2015)
        with col2:
            monthly_rent = st.number_input("월세 (만원, 전세면 0)", min_value=0, value=50, step=5)
            floor = st.number_input("층수", min_value=1, max_value=50, value=3)

        options = st.multiselect("옵션", OPTIONS_LIST, default=["에어컨", "세탁기", "냉장고"])

        submitted = st.form_submit_button("✨ 릴스 생성", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# 오른쪽: 결과
# ---------------------------------------------------------------------------

with right:
    st.subheader("생성 결과")

    if submitted:
        if not address.strip():
            st.error("주소를 입력해주세요.")
            st.stop()

        # --- 1. 주소 → 좌표 ---
        with st.status("📍 주소 좌표 변환 중...", expanded=True) as status:
            try:
                lat, lng = geocode(address)
                st.write(f"좌표: {lat}, {lng}")
            except Exception as e:
                status.update(label="❌ 주소 변환 실패", state="error")
                st.error(str(e))
                st.stop()

            # --- 2. 지하철역 ---
            status.update(label="🚇 주변 지하철역 검색 중...")
            try:
                subway_list = find_nearby_subways(lat, lng)
                for s in subway_list:
                    st.write(f"• {s['station']} 도보 {s['walk_min']}분")
            except Exception as e:
                st.warning(f"지하철 정보를 가져오지 못했습니다: {e}")
                subway_list = []

            # --- 3. 지도 이미지 ---
            status.update(label="🗺️ 지도 이미지 다운로드 중...")
            map_path = str(OUTPUT_DIR / f"map_{address[:10].replace(' ', '_')}.png")
            try:
                download_static_map(lat, lng, subway_list, map_path)
                st.write("지도 이미지 저장 완료")
            except Exception as e:
                st.warning(f"지도 이미지 실패: {e}")
                map_path = None

            # --- 4. 거리뷰 ---
            status.update(label="📸 거리뷰 스크린샷 촬영 중...")
            sv_path = str(OUTPUT_DIR / f"sv_{address[:10].replace(' ', '_')}.png")
            try:
                take_street_view(lat, lng, sv_path)
                st.write("거리뷰 저장 완료")
            except Exception as e:
                st.warning(f"거리뷰 실패: {e}")
                sv_path = None

            # --- 5. AI 카피 ---
            status.update(label="✍️ AI 광고 카피 생성 중...")
            try:
                copy = generate_copy(
                    address=address,
                    floor=int(floor),
                    size_pyeong=float(size_pyeong),
                    deposit=int(deposit),
                    monthly_rent=int(monthly_rent),
                    options=list(options),
                    year_built=int(year_built),
                    subway_list=subway_list,
                )
            except Exception as e:
                status.update(label="❌ 카피 생성 실패", state="error")
                st.error(str(e))
                st.stop()

            # --- 6. DB 저장 ---
            room = Room(
                address=address,
                floor=int(floor),
                size_pyeong=float(size_pyeong),
                deposit=int(deposit),
                monthly_rent=int(monthly_rent),
                options=list(options),
                year_built=int(year_built),
                lat=lat,
                lng=lng,
                subway_info=subway_list,
            )
            room_id = db.insert_room(room)

            status.update(label="✅ 완료!", state="complete", expanded=False)

        # --- 결과 표시 ---
        st.divider()

        if map_path and Path(map_path).exists():
            st.image(map_path, caption="지도", use_container_width=True)

        if sv_path and Path(sv_path).exists():
            st.image(sv_path, caption="거리뷰", use_container_width=True)

        st.divider()
        st.markdown("### 📝 광고 카피")
        st.markdown(f"**후크:** {copy['hook']}")
        for f in copy["features"]:
            st.markdown(f"- {f}")
        st.markdown(f"**CTA:** {copy['cta']}")

        hashtag_str = " ".join(copy["hashtags"])
        st.text_area("해시태그 (복사용)", hashtag_str, height=80)

        st.caption(f"매물 ID: {room_id} | 저장됨")

    else:
        st.info("왼쪽에서 매물 정보를 입력하고 '릴스 생성' 버튼을 눌러주세요.")
