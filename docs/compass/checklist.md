# Checklist

## Phase 1 — 코어 파이프라인

### 1-1. 프로젝트 기반 세팅
- [x] `pyproject.toml` 의존성 추가
- [x] `.env.example` 생성
- [x] 폴더 구조 및 `__init__.py` 생성

### 1-2. DB
- [x] `db/models.py` — rooms 스키마
- [x] `db/database.py` — SQLite CRUD

### 1-3. 지도 서비스
- [x] `services/map/geocoding.py` — 주소 → 좌표
- [x] `services/map/subway/` — 지하철역 + 도보 거리 (로컬 CSV DB 기반, 호선별 최대 3개)
- [x] `services/map/static_map.py` — 지도 이미지 다운로드 (매물 빨강 마커 + 역 파랑 마커)
- [x] `assets/data/subway/` — 공공데이터 CSV (서울 1~9호선, 인천, 부산)

### 1-4. 스트리트뷰
- [x] `services/street/playwright_shot.py` — 스크린샷
- [x] fallback: 위성지도 이미지

### 1-5. AI 카피
- [x] `services/ai/copy_writer.py` — gpt-5-mini 카피 생성
- [x] SYSTEM_PROMPT에 허위·과장 광고 금지 명시
- [x] 프롬프트 검증 (특징 3줄, 해시태그, narrations)

### 1-6. 영상 생성
- [x] `services/video/templates.py` — 슬라이드 이미지 합성
- [x] `services/video/renderer.py` — MoviePy 영상 렌더링 (슬라이드별 오디오 싱크)
- [x] 한글 폰트 assets/fonts/ 배치 (에이투지체 전체 + NanumGothic)
- [ ] BGM 파일 assets/bgm/ 배치

### 1-7. Streamlit UI
- [x] `app.py` — 입력 폼 (주소, 가격, 평수, 층, 준공연도, 옵션, 실내사진, 전세대출, 코멘트)
- [x] 파이프라인 실행 + 진행 상태 표시
- [x] 영상 다운로드 버튼
- [x] 광고 카피 복사 버튼

---

## Phase 2 — 관리 기능
- [x] 매물 목록 사이드바 (순서 기반 번호 표시)
- [x] 재생성 버튼
- [x] 매물 삭제

---

## Phase 3 — TTS + 영상 퀄리티 개선

### TTS 서버
- [x] `tts_server/main.py` — FastAPI POST /synthesize
- [x] `tts_server/model.py` — edge-tts 기반 (ko-KR-SunHiNeural)
- [x] `services/ai/tts.py` — TTS 서버 HTTP 호출

### 편의시설 검색 개선
- [x] `find_nearby_shops(region_hint)` — 지역명 prefix 검색

### 슬라이드 디자인 개선
- [x] 폰트 에이투지체-7Bold 적용 (fallback: NanumGothic)
- [x] 자막 위치: 인스타 dead zone 위 배치 (REEL_DEAD_BOTTOM=380)
- [x] 자막 크기: 62px

### 개발 도구
- [x] `tests/video/gen_slides.py` — 슬라이드 이미지+대본 생성 스크립트

---

## Phase 4 — Instagram 업로드
- [ ] 스토리지 연동 (S3 / Cloudflare R2)
- [ ] `services/upload/instagram.py` 구현
- [ ] 위치 태그 2개 (사무소 + 매물)
- [ ] Streamlit 업로드 버튼

---

## Phase 5 — 확장
- [ ] n8n 래핑
- [ ] Supabase 마이그레이션
- [ ] 경쟁 매물 비교
- [ ] 점수 매기기
- [ ] 채광 분석

---

## 보류 중인 개선
- [ ] 대본 템플릿 적용 (사용자가 별도 제공 예정)
- [ ] BGM 파일 assets/bgm/ 배치
- [ ] app.py에 region_hint 전달 반영
