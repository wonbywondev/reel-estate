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
- [x] 프롬프트 검증 (후크, 특징 3줄, 해시태그)

### 1-6. 영상 생성
- [x] `services/video/templates.py` — 슬라이드 이미지 합성 (cover crop, 5슬라이드)
- [x] `services/video/renderer.py` — MoviePy 영상 렌더링 (BGM 선택적)
- [x] 한글 폰트 assets/fonts/ 배치
- [ ] BGM 파일 assets/bgm/ 배치

### 1-7. Streamlit UI
- [x] `app.py` — 입력 폼 (주소, 가격, 평수, 층, 준공연도, 옵션 멀티셀렉트)
- [x] 파이프라인 실행 + 진행 상태 표시
- [ ] 영상 다운로드 버튼
- [x] 광고 카피 복사 버튼 (해시태그 text_area)

---

## Phase 2 — 관리 기능
- [ ] 매물 목록 사이드바
- [ ] 재생성 버튼
- [ ] 매물 삭제

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

## 보류 중인 개선 계획 (plans/mossy-weaving-hammock.md)

### 영상 v2 — TTS + 자막 기반 개편
- [ ] `services/ai/tts.py` — OpenAI TTS로 슬라이드별 나레이션 생성
- [ ] `services/ai/copy_writer.py` — hook 제거, narrations 5+N개 추가
- [ ] `services/video/templates.py` — 슬라이드 하단 자막 오버레이, slide_interior 추가
- [ ] `services/video/renderer.py` — 슬라이드별 오디오 싱크 지원
- [ ] `db/models.py` — loan_available, agent_comment, interior_paths 필드 추가
- [ ] `app.py` — 실내사진 업로드, 전세대출가능 체크박스, 중개자코멘트 입력 추가
