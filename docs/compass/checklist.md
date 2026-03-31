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
- [x] `assets/data/subway/` — 공공데이터 CSV (서울 1~9호선, 인천 연수구)

### 1-4. 스트리트뷰
- [x] `services/street/playwright_shot.py` — 스크린샷
- [x] fallback: 위성지도 이미지

### 1-5. AI 카피
- [x] `services/ai/copy_writer.py` — gpt-5-mini 카피 생성
- [x] SYSTEM_PROMPT에 허위·과장 광고 금지 명시
- [x] 프롬프트 검증 (특징 3줄, 해시태그, narrations)

### 1-6. 영상 생성
- [x] `services/video/templates.py` — 슬라이드 이미지 합성 (cover crop, 9슬라이드)
- [x] `services/video/renderer.py` — MoviePy 영상 렌더링 (슬라이드별 오디오 싱크)
- [x] 한글 폰트 assets/fonts/ 배치
- [ ] BGM 파일 assets/bgm/ 배치

### 1-7. Streamlit UI
- [x] `app.py` — 입력 폼 (주소, 가격, 평수, 층, 준공연도, 옵션, 실내사진, 전세대출, 코멘트)
- [x] 파이프라인 실행 + 진행 상태 표시
- [x] 영상 다운로드 버튼 (st.video + st.download_button)
- [x] 광고 카피 복사 버튼 (해시태그 text_area)

---

## Phase 2 — 관리 기능
- [x] 매물 목록 사이드바 (순서 기반 번호 표시)
- [x] 재생성 버튼
- [x] 매물 삭제

---

## Phase 3 — Instagram 업로드
- [ ] 스토리지 연동 (S3 / Cloudflare R2)
- [ ] `services/upload/instagram.py` 구현
- [ ] 위치 태그 2개 (사무소 + 매물)
- [ ] Streamlit 업로드 버튼

---

## Phase 4 — 확장
- [ ] n8n 래핑
- [ ] Supabase 마이그레이션
- [ ] 경쟁 매물 비교
- [ ] 점수 매기기
- [ ] 채광 분석

---

## 영상 v2 — TTS + 자막 기반 개편
- [x] `services/ai/tts.py` — OpenAI TTS 인터페이스 (현재 403 — 프로젝트 권한 없음)
- [x] `services/ai/copy_writer.py` — hook 제거, narrations 동적 생성 (슬라이드 수 반영)
- [x] `services/video/templates.py` — 슬라이드 하단 자막 오버레이, slide_interior 추가
- [x] `services/video/renderer.py` — 슬라이드별 오디오 싱크 지원
- [x] `db/models.py` — loan_available, agent_comment, interior_paths 필드 추가
- [x] `app.py` — 실내사진 업로드, 전세대출가능 체크박스, 중개자코멘트 입력 추가

---

## 영상 v3 — 슬라이드 구성 개편
- [x] 첫 슬라이드: 동네 이름 자막 (썸네일 겸용) — `slide_title()`
- [x] 지도 2장 분리: 넓은 축척(동네) → 좁은 축척(지하철역)
- [x] 근처 편의시설 슬라이드 — `services/map/nearby.py` (네이버 Local Search API)
  - 대형마트/다이소 반경 10km 최대 5개, 편의점 반경 1km 최대 1개
- [x] `db/models.py` — shops_info 필드 추가
- [x] `copy_writer.py` SYSTEM_PROMPT 허위·과장 광고 금지 명시
- [ ] 구체적인 대본 템플릿 적용 (사용자가 별도 제공 예정)

---

## TTS 서버 — HuggingFace 자체 호스팅
- [ ] `tts_server/main.py` — FastAPI POST /synthesize
- [ ] `tts_server/model.py` — facebook/mms-tts-kor 로드 + 추론 (CPU)
- [ ] `services/ai/tts.py` 수정 — OpenAI 대신 TTS 서버 HTTP 호출
- [ ] 서버 실행 스크립트 및 의존성 정리
