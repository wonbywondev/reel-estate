"""부동산 릴스 자동 생성기 — Streamlit 앱."""
from pathlib import Path

import streamlit as st

from db.database import Database
from db.models import Room
from services.map.geocoding import geocode
from services.map.subway import find_nearby_subways
from services.map.static_map import download_static_map, download_static_map_wide
from services.map.nearby import find_nearby_shops
from services.street.playwright_shot import take_street_view
from services.ai.copy_writer import generate_copy
from services.ai.tts import text_to_speech
from services.video.templates import (
    slide_title, slide_map, slide_street, slide_interior,
    slide_subway, slide_room_options, slide_price,
    slide_nearby_shops, slide_cta,
)
from services.video.renderer import render_video

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
# 페이지 설정
# ---------------------------------------------------------------------------

st.set_page_config(page_title="부동산 릴스 생성기", page_icon="🏠", layout="wide")
st.title("🏠 부동산 릴스 자동 생성기")

# ---------------------------------------------------------------------------
# 사이드바: 매물 목록
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("📋 매물 목록")

    rooms = db.list_rooms()
    if not rooms:
        st.caption("아직 생성된 매물이 없습니다.")
    else:
        for idx, room in enumerate(rooms, 1):
            with st.expander(f"#{idx} {room.address[:20]}", expanded=False):
                price = (
                    f"전세 {room.deposit:,}만원"
                    if room.monthly_rent == 0
                    else f"보증 {room.deposit:,} / 월세 {room.monthly_rent}만원"
                )
                st.caption(f"{price} | {room.size_pyeong}평 {room.floor}층")

                slug = room.address[:10].replace(' ', '_')
                video_path = str(OUTPUT_DIR / f"reels_{slug}.mp4")

                if Path(video_path).exists():
                    with open(video_path, "rb") as vf:
                        st.download_button(
                            label="⬇️ MP4",
                            data=vf,
                            file_name=Path(video_path).name,
                            mime="video/mp4",
                            key=f"dl_{room.id}",
                        )

                if st.button("🔄 재생성", key=f"regen_{room.id}"):
                    st.session_state["regen_room_id"] = room.id
                    st.rerun()

                if st.button("🗑️ 삭제", key=f"del_{room.id}"):
                    if room.id:
                        db.delete_room(room.id)
                    st.rerun()

# ---------------------------------------------------------------------------
# 재생성 처리
# ---------------------------------------------------------------------------

regen_room: Room | None = None
if "regen_room_id" in st.session_state:
    regen_room = db.get_room(st.session_state.pop("regen_room_id"))

# ---------------------------------------------------------------------------
# 레이아웃
# ---------------------------------------------------------------------------

left, right = st.columns([1, 1], gap="large")

# ---------------------------------------------------------------------------
# 왼쪽: 입력 폼
# ---------------------------------------------------------------------------

with left:
    st.subheader("매물 정보 입력")

    defaults = {
        "address": regen_room.address if regen_room else "",
        "deposit": regen_room.deposit if regen_room else 1000,
        "monthly_rent": regen_room.monthly_rent if regen_room else 50,
        "size_pyeong": regen_room.size_pyeong if regen_room else 10.0,
        "floor": regen_room.floor if regen_room else 3,
        "year_built": regen_room.year_built if regen_room else 2015,
        "options": regen_room.options if regen_room else ["에어컨", "세탁기", "냉장고"],
        "loan_available": regen_room.loan_available if regen_room else False,
        "agent_comment": regen_room.agent_comment if regen_room else "",
        "facing": regen_room.facing if regen_room else "",
        "room_config": regen_room.room_config if regen_room else "",
    }

    with st.form("room_form"):
        address = st.text_input("도로명 주소 *", value=defaults["address"],
                                placeholder="예: 서울시 강남구 역삼동 123")

        col1, col2 = st.columns(2)
        with col1:
            deposit = st.number_input("보증금 (만원)", min_value=0,
                                      value=defaults["deposit"], step=100)
            size_pyeong = st.number_input("평수", min_value=1.0,
                                          value=float(defaults["size_pyeong"]), step=0.5)
            year_built = st.number_input("준공연도", min_value=1970, max_value=2030,
                                         value=defaults["year_built"])
        with col2:
            monthly_rent = st.number_input("월세 (만원, 전세면 0)", min_value=0,
                                           value=defaults["monthly_rent"], step=5)
            floor = st.number_input("층수", min_value=1, max_value=50,
                                    value=defaults["floor"])

        options = st.multiselect("옵션", OPTIONS_LIST, default=defaults["options"])

        col3, col4 = st.columns(2)
        with col3:
            facing = st.text_input("방향 (선택)", value=defaults["facing"],
                                   placeholder="예: 남향, 남동향")
        with col4:
            room_config = st.text_input("방 구성 (선택)", value=defaults["room_config"],
                                        placeholder="예: 방2 거실1 화장실1")

        loan_available = st.checkbox("전세 대출 가능", value=defaults["loan_available"])
        agent_comment = st.text_area("중개자 코멘트 (선택)",
                                     value=defaults["agent_comment"] or "",
                                     placeholder="예: 햇빛이 잘 들고 조용한 주거 환경입니다.",
                                     height=80)

        submitted = st.form_submit_button("✨ 릴스 생성", use_container_width=True, type="primary")

    # form 밖: 사진 업로드/촬영
    import hashlib
    if "interior_photos" not in st.session_state:
        st.session_state["interior_photos"] = []
    if "_uploader_key" not in st.session_state:
        st.session_state["_uploader_key"] = 0

    # 액션 처리
    _action = st.session_state.pop("_photo_action", None)
    if _action:
        _p = st.session_state["interior_photos"]
        _op, _idx = _action
        if _op == "del" and 0 <= _idx < len(_p):
            _p.pop(_idx)
            st.session_state["_uploader_key"] += 1
            st.rerun()
        elif _op == "up" and 0 < _idx < len(_p):
            _p[_idx], _p[_idx - 1] = _p[_idx - 1], _p[_idx]
            st.rerun()
        elif _op == "down" and 0 <= _idx < len(_p) - 1:
            _p[_idx], _p[_idx + 1] = _p[_idx + 1], _p[_idx]
            st.rerun()

    st.markdown("**실내 사진** (선택, 최대 5장)")
    tab_upload, tab_camera = st.tabs(["📁 파일 업로드", "📷 카메라 촬영"])
    _uk = st.session_state["_uploader_key"]
    with tab_upload:
        uploaded = st.file_uploader(
            "사진 선택",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"interior_uploader_{_uk}",
        )
        if uploaded:
            existing = {p["hash"] for p in st.session_state["interior_photos"]}
            for f in uploaded:
                raw = f.read()
                h = hashlib.md5(raw).hexdigest()
                if h not in existing and len(st.session_state["interior_photos"]) < 5:
                    st.session_state["interior_photos"].append({"data": raw, "hash": h})
                    existing.add(h)
    with tab_camera:
        shot = st.camera_input("촬영", label_visibility="collapsed")
        if shot:
            raw = shot.read()
            h = hashlib.md5(raw).hexdigest()
            existing = {p["hash"] for p in st.session_state["interior_photos"]}
            if h not in existing and len(st.session_state["interior_photos"]) < 5:
                st.session_state["interior_photos"].append({"data": raw, "hash": h})

    photos: list[dict] = st.session_state["interior_photos"]
    if photos:
        st.caption("사진 설명 (슬라이드 하단 자막, 선택)")
        for i, photo_item in enumerate(photos):
            col_img, col_lbl, col_btn = st.columns([1, 2, 1])
            with col_img:
                st.image(photo_item["data"], use_container_width=True)
            with col_lbl:
                st.text_input(
                    f"사진 {i+1} 설명",
                    key=f"interior_label_{i}",
                    placeholder="예: 거실, 주방, 안방",
                    label_visibility="collapsed",
                )
            with col_btn:
                b1, b2, b3 = st.columns(3)
                with b1:
                    if i > 0 and st.button("↑", key=f"move_up_{i}"):
                        st.session_state["_photo_action"] = ("up", i)
                with b2:
                    if i < len(photos) - 1 and st.button("↓", key=f"move_down_{i}"):
                        st.session_state["_photo_action"] = ("down", i)
                with b3:
                    if st.button("🗑️", key=f"del_photo_{i}"):
                        st.session_state["_photo_action"] = ("del", i)

# ---------------------------------------------------------------------------
# 오른쪽: 결과
# ---------------------------------------------------------------------------

with right:
    st.subheader("생성 결과")

    if submitted:
        if not address or not address.strip():
            st.error("주소를 입력해주세요.")
            st.stop()
        assert isinstance(address, str)

        slug = address[:10].replace(' ', '_')

        # 실내 사진 저장 + 레이블 수집
        interior_paths: list[str] = []
        interior_labels: list[str] = []
        for i, photo_item in enumerate((st.session_state.get("interior_photos") or [])[:5]):
            ipath = str(OUTPUT_DIR / f"interior_{slug}_{i}.jpg")
            Path(ipath).write_bytes(photo_item["data"])
            interior_paths.append(ipath)
            interior_labels.append(st.session_state.get(f"interior_label_{i}", ""))

        with st.status("📍 주소 좌표 변환 중...", expanded=True) as status:
            try:
                lat, lng = geocode(address)
                st.write(f"좌표: {lat}, {lng}")
            except Exception as e:
                status.update(label="❌ 주소 변환 실패", state="error")
                st.error(str(e))
                st.stop()

            status.update(label="🚇 주변 지하철역 검색 중...")
            try:
                subway_list = find_nearby_subways(lat, lng)
                for s in subway_list:
                    st.write(f"• {s['station']} 도보 {s['walk_min']}분")
            except Exception as e:
                st.warning(f"지하철 정보를 가져오지 못했습니다: {e}")
                subway_list = []

            status.update(label="🗺️ 지도 이미지 다운로드 중...")
            wide_map_path = str(OUTPUT_DIR / f"map_wide_{slug}.png")
            try:
                download_static_map_wide(lat, lng, wide_map_path)
                st.write("넓은 지도 이미지 저장 완료")
            except Exception as e:
                st.warning(f"넓은 지도 이미지 실패: {e}")
                wide_map_path = None

            map_path = str(OUTPUT_DIR / f"map_{slug}.png")
            try:
                download_static_map(lat, lng, subway_list, map_path)
                st.write("지역 지도 이미지 저장 완료")
            except Exception as e:
                st.warning(f"지도 이미지 실패: {e}")
                map_path = None

            status.update(label="🛒 근처 편의시설 검색 중...")
            try:
                region_hint = " ".join(address.split()[:2])
                shops_list = find_nearby_shops(lat, lng, region_hint=region_hint)
                for s in shops_list:
                    st.write(f"• {s['name']} ({s['distance']}m)")
            except Exception as e:
                st.warning(f"편의시설 정보를 가져오지 못했습니다: {e}")
                st.exception(e)
                shops_list = []

            status.update(label="📸 거리뷰 스크린샷 촬영 중...")
            sv_path = str(OUTPUT_DIR / f"sv_{slug}.png")
            try:
                take_street_view(lat, lng, sv_path)
                st.write("거리뷰 저장 완료")
            except Exception as e:
                st.warning(f"거리뷰 실패: {e}")
                sv_path = None

            status.update(label="✍️ AI 대본 및 카피 생성 중...")
            # 실제 편의시설 카테고리 목록 확정
            mart_kw = ("슈퍼,마트", "종합생활용품", "시장", "백화점")
            _shop_cats: list[str] = []
            if any(any(kw in s.get("category", "") for kw in mart_kw) for s in shops_list):
                _shop_cats.append("마트 / 시장")
            if any("편의점" in s.get("category", "") for s in shops_list):
                _shop_cats.append("편의점")
            if any(any(kw in s.get("category", "") for kw in ("영화관", "서점")) for s in shops_list):
                _shop_cats.append("영화관 / 서점")
            if any(any(kw in s.get("category", "") for kw in ("공원", "근린공원")) for s in shops_list):
                _shop_cats.append("공원")

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
                    loan_available=bool(loan_available),
                    agent_comment=agent_comment or None,
                    interior_count=len(interior_paths),
                    interior_labels=interior_labels,
                    shop_categories=_shop_cats,
                )
            except Exception as e:
                status.update(label="❌ 카피 생성 실패", state="error")
                st.error(str(e))
                st.stop()

            # TTS 생성
            status.update(label="🔊 나레이션 음성 생성 중...")
            narrations: list[str] = copy.get("narrations", [])
            audio_paths: list[str | None] = []
            for i, narr in enumerate(narrations):
                try:
                    apath = str(OUTPUT_DIR / f"narr_{slug}_{i}.mp3")
                    text_to_speech(narr, apath)
                    audio_paths.append(apath)
                    st.write(f"• 나레이션 {i+1}: {narr}")
                except Exception as e:
                    st.warning(f"나레이션 {i+1} TTS 실패: {e}")
                    audio_paths.append(None)

            # 슬라이드 구성
            status.update(label="🎬 영상 렌더링 중...")
            video_path = str(OUTPUT_DIR / f"reels_{slug}.mp4")

            def _audio(idx: int) -> str | None:
                return audio_paths[idx] if idx < len(audio_paths) else None

            try:
                price_str = (
                    f"보증 {int(deposit):,} / 월 {int(monthly_rent)}만원"
                    if int(monthly_rent) else f"전세 {int(deposit):,}만원"
                )

                ai = 0  # audio index
                slides_data: list[tuple] = []

                # 1. 썸네일
                slides_data.append((slide_title(address, price_str), 2.0, _audio(ai))); ai += 1
                # 2. 넓은 지도
                slides_data.append((slide_map(wide_map_path or ""), 2.0, _audio(ai))); ai += 1
                # 3. 거리뷰
                slides_data.append((slide_street(sv_path or "", subtitle=address), 3.0, _audio(ai))); ai += 1
                # 4. 실내 사진
                for i, ipath in enumerate(interior_paths):
                    lbl = interior_labels[i] if i < len(interior_labels) else ""
                    slides_data.append((slide_interior(ipath, subtitle=lbl, label=lbl), 3.0, _audio(ai))); ai += 1
                # 5. 지하철역 지도 (자막 없음)
                slides_data.append((slide_subway(subway_list, map_path=map_path or ""), 3.0, _audio(ai))); ai += 1
                # 6. 편의시설 — 카테고리별 (자막 없음)
                mart_kw = ("슈퍼,마트", "종합생활용품", "시장", "백화점")
                mart_shops = [s for s in shops_list if any(kw in s.get("category", "") for kw in mart_kw)]
                if mart_shops:
                    slides_data.append((slide_nearby_shops(mart_shops, header="🏪 마트 / 시장"), 3.0, _audio(ai))); ai += 1
                conv_shops = [s for s in shops_list if "편의점" in s.get("category", "")]
                if conv_shops:
                    slides_data.append((slide_nearby_shops(conv_shops, header="🏪 편의점"), 3.0, _audio(ai))); ai += 1
                ent_shops = [s for s in shops_list if any(kw in s.get("category", "") for kw in ("영화관", "서점"))]
                if ent_shops:
                    slides_data.append((slide_nearby_shops(ent_shops, header="🎬 영화관 / 서점"), 3.0, _audio(ai))); ai += 1
                park_shops = [s for s in shops_list if any(kw in s.get("category", "") for kw in ("공원", "근린공원"))]
                if park_shops:
                    slides_data.append((slide_nearby_shops(park_shops, header="🌳 공원"), 3.0, _audio(ai))); ai += 1
                # 7. 옵션 + 방향 + 준공연도 + 방 구성 (자막 없음)
                slides_data.append((slide_room_options(
                    floor=int(floor), size_pyeong=float(size_pyeong), year_built=int(year_built),
                    options=list(options), facing=str(facing) if facing else "",
                    room_config=str(room_config) if room_config else "",
                ), 3.0, _audio(ai))); ai += 1
                # 8. 가격 + 전세대출 (자막 없음)
                slides_data.append((slide_price(
                    deposit=int(deposit), monthly_rent=int(monthly_rent),
                    loan_available=bool(loan_available), address=address,
                ), 3.0, _audio(ai))); ai += 1
                # 9. CTA
                slides_data.append((slide_cta(copy["cta"], copy["hashtags"]), 3.0, _audio(ai)))

                render_video(slides_data, video_path)
                st.write("영상 저장 완료")
            except Exception as e:
                st.warning(f"영상 렌더링 실패: {e}")
                video_path = None

            # DB 저장
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
                loan_available=bool(loan_available),
                agent_comment=agent_comment or None,
                interior_paths=interior_paths,
                interior_labels=interior_labels,
                shops_info=shops_list,
                facing=str(facing) if facing else None,
                room_config=str(room_config) if room_config else None,
            )
            room_id = db.insert_room(room)
            if video_path:
                db.update_video_path(room_id, video_path)

            status.update(label="✅ 완료!", state="complete", expanded=False)

        # --- 결과 표시 ---
        st.divider()

        if video_path and Path(video_path).exists():
            st.markdown("### 🎬 생성된 릴스")
            st.video(video_path)
            with open(video_path, "rb") as vf:
                st.download_button(
                    label="⬇️ MP4 다운로드",
                    data=vf,
                    file_name=Path(video_path).name,
                    mime="video/mp4",
                    use_container_width=True,
                )

        st.divider()

        col_map, col_sv = st.columns(2)
        with col_map:
            if map_path and Path(map_path).exists():
                st.image(map_path, caption="지도", use_container_width=True)
        with col_sv:
            if sv_path and Path(sv_path).exists():
                st.image(sv_path, caption="거리뷰", use_container_width=True)

        st.divider()
        st.markdown("### 📝 광고 카피")
        for feat in copy["features"]:
            st.markdown(f"- {feat}")
        st.markdown(f"**CTA:** {copy['cta']}")

        hashtag_str = " ".join(copy["hashtags"])
        st.text_area("해시태그 (복사용)", hashtag_str, height=80)

        st.caption(f"매물 ID: {room_id} | 저장됨")

    else:
        st.info("왼쪽에서 매물 정보를 입력하고 '릴스 생성' 버튼을 눌러주세요.")
