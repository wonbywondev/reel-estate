# Plan — 구현 순서

## 원칙
- 각 Phase가 독립적으로 동작 가능한 상태로 완료
- Phase 1 완료 시 실제로 영상이 나와야 함
- 외부 API 의존성이 있는 모듈은 mock 데이터로 먼저 구조 검증

---

## Phase 1 — 코어 파이프라인 (MVP)

### 1-1. 프로젝트 기반 세팅
- `pyproject.toml` 의존성 추가 (streamlit, moviepy, playwright, openai, requests, python-dotenv)
- `.env` 템플릿 생성 (`NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `OPENAI_API_KEY`)
- 폴더 구조 생성 및 `__init__.py` 파일 배치

### 1-2. DB 세팅
- `db/models.py` — rooms 테이블 스키마 정의
- `db/database.py` — SQLite 연결, insert/select CRUD

### 1-3. 지도 서비스
- `services/map/geocoding.py` — 도로명 주소 → 위도/경도 (네이버 Geocoding API)
- `services/map/subway.py` — 근처 지하철역 검색 + 도보 거리 계산 (네이버 장소 검색으로 반경 500m 내 지하철역 조회 → 도보 거리 최단 1개 반환)
- `services/map/static_map.py` — Static Map 이미지 다운로드 (지하철역 마커 포함)

### 1-4. 스트리트뷰 서비스
- `services/street/playwright_shot.py` — Playwright로 네이버 스트리트뷰 스크린샷
  - 실패 시 위성지도 이미지로 자동 fallback

### 1-5. AI 카피 서비스
- `services/ai/copy_writer.py` — gpt-5-mini로 광고 카피 생성
  - 입력: 방 정보 + 지하철 데이터
  - 출력: 후크 문장, 특징 3줄, 해시태그 목록

### 1-6. 영상 생성 서비스
- `services/video/templates.py` — 슬라이드 레이아웃 (PIL로 이미지 합성)
- `services/video/renderer.py` — MoviePy로 5슬라이드 영상 렌더링 (BGM 포함, 9:16)

### 1-7. Streamlit UI
- `app.py` — 입력 폼 (주소, 층, 평수, 보증금, 월세, 옵션 체크박스, 준공연도)
- 생성 버튼 → 파이프라인 순차 실행 → 진행 상태 표시
- 결과: 영상 미리보기 + 다운로드 버튼 + 광고 카피 텍스트 복사

---

## Phase 2 — 관리 기능

- Streamlit 사이드바에 매물 목록 (SQLite 조회)
- 매물별 재생성 버튼
- 매물 삭제

---

## Phase 3 — Instagram 업로드

- S3 또는 Cloudflare R2 임시 스토리지 연동
- `services/upload/instagram.py` — Instagram Graph API 릴스 업로드
  - 위치 태그: 사무소 주소 + 매물 주소 2개
- Streamlit에 "인스타 업로드" 버튼 추가
- `.env`에 `INSTAGRAM_ACCESS_TOKEN`, `AGENCY_ADDRESS` 추가

---

## Phase 4 — 확장 (선택)

- n8n 워크플로우로 각 서비스 래핑
- SQLite → Supabase 마이그레이션
- 경쟁 매물 가격 비교 (네이버 부동산 / 직방 크롤링)
- 매물 점수 매기기
- 채광 분석 (주변 고층 건물 데이터 활용)
