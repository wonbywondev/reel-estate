# Checklist

## Phase 1 — 코어 파이프라인

### 1-1. 프로젝트 기반 세팅
- [ ] `pyproject.toml` 의존성 추가
- [ ] `.env.example` 생성
- [ ] 폴더 구조 및 `__init__.py` 생성

### 1-2. DB
- [ ] `db/models.py` — rooms 스키마
- [ ] `db/database.py` — SQLite CRUD

### 1-3. 지도 서비스
- [ ] `services/map/geocoding.py` — 주소 → 좌표
- [ ] `services/map/subway.py` — 지하철역 + 도보 거리
- [ ] `services/map/static_map.py` — 지도 이미지 다운로드

### 1-4. 스트리트뷰
- [ ] `services/street/playwright_shot.py` — 스크린샷
- [ ] fallback: 위성지도 이미지

### 1-5. AI 카피
- [ ] `services/ai/copy_writer.py` — gpt-5-mini 카피 생성
- [ ] 프롬프트 검증 (후크, 특징 3줄, 해시태그)

### 1-6. 영상 생성
- [ ] `services/video/templates.py` — 슬라이드 이미지 합성
- [ ] `services/video/renderer.py` — MoviePy 영상 렌더링
- [ ] 한글 폰트 assets/fonts/ 배치
- [ ] BGM 파일 assets/bgm/ 배치

### 1-7. Streamlit UI
- [ ] `app.py` — 입력 폼
- [ ] 파이프라인 실행 + 진행 상태 표시
- [ ] 영상 다운로드 버튼
- [ ] 광고 카피 복사 버튼

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
