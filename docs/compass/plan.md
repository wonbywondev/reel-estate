# Plan — 구현 순서

## 원칙
- 각 Phase가 독립적으로 동작 가능한 상태로 완료
- 외부 API 의존성이 있는 모듈은 mock 데이터로 먼저 구조 검증

---

## Phase 1 — 코어 파이프라인 ✅ 완료

### 1-1. 프로젝트 기반 세팅 ✅
### 1-2. DB ✅
### 1-3. 지도 서비스 ✅
- `geocoding.py` — 네이버 Geocoding API
- `subway/` — 공공데이터 CSV (서울 1~9호선, 인천, 부산) + Haversine + Directions API
- `static_map.py` — level=15 좁은 지도 + level=12 넓은 지도

### 1-4. 스트리트뷰 ✅
- Playwright → pano_id 추출 → 캡처 (JS dialog 숨김)
- fallback: 위성지도

### 1-5. AI 카피 ✅
- gpt-5-mini (temperature 미지원)
- narrations 동적 생성 (슬라이드 수 반영)
- 허위·과장 광고 금지 명시

### 1-6. 영상 생성 ✅
- templates.py: 9슬라이드 (title, map×2, street, interior×N, room_info, shops, copy, cta)
- renderer.py: 슬라이드별 오디오 싱크 (None이면 무음)

### 1-7. Streamlit UI ✅
- 입력: 주소, 가격, 평수, 층, 준공연도, 옵션, 실내사진(최대5), 전세대출, 중개자코멘트
- 사이드바: 매물 목록 (순서 기반 번호), 재생성, 삭제, MP4 다운로드

---

## Phase 2 — 관리 기능 ✅ 완료

- 매물 목록 사이드바 (순서 기반 #1, #2...)
- 재생성 (기존 정보 폼 프리필)
- 매물 삭제

---

## Phase 2.5 — 영상 v2/v3 개편 ✅ 완료

### 영상 v2 — TTS + 자막
- narrations 기반 슬라이드별 자막 오버레이 구현

### 영상 v3 — 슬라이드 구성 개편
- 첫 슬라이드: 동네 이름 (썸네일)
- 지도 2장: 넓은 축척 → 좁은 축척
- 편의시설 슬라이드: 대형마트/다이소(10km), 편의점(1km)

---

## Phase 3 — TTS + 영상 퀄리티 개선 ✅ 완료

### 3-1. TTS 서버 ✅
- edge-tts (Microsoft Azure) 기반 `tts_server/`
- `POST /synthesize` → MP3 bytes 반환
- 기본 음성: `ko-KR-SunHiNeural`, `TTS_VOICE` 환경변수로 변경 가능

### 3-2. 편의시설 검색 개선 ✅
- `find_nearby_shops(lat, lng, region_hint)` — 지역명 prefix로 검색 정확도 향상

### 3-3. 슬라이드 디자인 개선 ✅
- 폰트: 에이투지체-7Bold (fallback: NanumGothic)
- 자막 위치: 인스타 dead zone(하단 380px) 위
- 자막 크기: 62px

### 3-4. 개발 도구 ✅
- `tests/video/gen_slides.py` — TTS 없이 슬라이드 이미지+대본만 빠르게 생성
  - `output/{slug}_{timestamp}/` 폴더에 슬라이드 PNG + script.txt + meta.json 저장

---

## Phase 4 — Instagram 업로드 ✅ 완료

- API 키 발급 완료 (INSTA_ACCOUNT_ID, INSTA_ACCESS_TOKEN, INSTA_GRAPH_API_TOKEN)
- Facebook 페이지(Reel-estate) ↔ Instagram(mukjiithecat) 연결 완료
- `services/instagram/uploader.py` 구현 완료
  - 인증: 사용자 토큰 → 페이지 토큰 자동 교환
  - 공개 URL: Cloudflare Tunnel (cloudflared) 자동 실행 — ngrok-free.dev는 Instagram에서 차단됨
  - 업로드 흐름: 로컬 파일 서버 → cloudflared 터널 → 컨테이너 생성 → polling → 게시
- Streamlit 업로드 버튼 구현 완료 (app.py)
- 영상 재인코딩 + R2 업로드 구현 완료
  - ffmpeg CBR 3.5Mbps / baseline / 48kHz로 재인코딩 후 R2 presigned URL → Instagram API
  - trycloudflare.com, ngrok-free.dev 모두 Meta 서버에서 차단 확인 → R2로 대체
- 위치 태그 2개 (사무소 + 매물) — 추후 구현

---

## Phase 5 — 확장 (선택)

- n8n 워크플로우로 각 서비스 래핑
- SQLite → Supabase 마이그레이션
- 경쟁 매물 가격 비교 (네이버 부동산 / 직방 크롤링)
- 매물 점수 매기기
- 채광 분석 (주변 고층 건물 데이터 활용)

---

---

## Phase 3.5 — 슬라이드 v4 개편 (다음 구현)

slides.md 기준 신규 구성으로 전면 개편.

### 변경 사항
- `slide_title`: 동네명 → 주소 + 가격
- 슬라이드 순서: title → 넓은지도 → 거리뷰 → 실내사진 → 지하철지도 → 편의시설(항목별 분리) → 옵션+방향+준공연도+방구성 → 가격+전세대출 → CTA
- `slide_copy`(AI 특징 3가지) 제거
- 편의시설 항목별 개별 슬라이드 분리 (마트류 / 편의점 / 영화관·서점 / 공원)
- 편의시설 검색: 영화관, 서점 추가
- 실내 사진: 업로드 시 레이블 입력 (ex. 방1, 거실, 도면), 도면 이미지 포함 가능
- 입력 필드 추가: 방향(텍스트), 방 구성(텍스트, ex. 방2 거실1 화장실1)
- 방정보 슬라이드 분리: 옵션+방향+준공연도+방구성 / 가격+전세대출
- DB 스키마 업데이트: facing(방향), room_config(방 구성), interior_labels(실내사진 레이블) 필드 추가

### 자막 원칙
- 각 슬라이드 자막은 **해당 슬라이드가 보여주는 정보를 그대로** 표현
- 다른 슬라이드 내용을 참조하거나 AI가 창작한 나레이션 사용 금지
- ex. 지하철 슬라이드 → "센트럴파크역 도보 3분 (775m)", 편의시설 슬라이드 → 해당 시설 이름+거리

### 추후 검토
- 네이버 부동산 비공식 API(`fin.land.naver.com/front-api/v1/article/basicInfo`)로 도면·방향 자동 수집
  - 현재: 이용약관 저촉 리스크로 보류, 직접 입력으로 대체

---

## 보류 중인 개선

- 대본 템플릿 적용 (사용자가 별도 제공 예정)
- BGM 파일 assets/bgm/ 배치
- app.py에도 region_hint 전달 반영
- 거리뷰: 건물 정면 뷰 자동 검증
