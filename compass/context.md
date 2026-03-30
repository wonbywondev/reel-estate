# Context — 부동산 릴스 자동 생성기

## 프로젝트 개요

공인중개사가 매물 정보를 입력하면, 네이버 지도 데이터를 자동 수집하고 AI 광고 카피와 릴스 영상을 생성해주는 도구.

**타겟 사용자**: 공인중개사 (소상공인)
**핵심 가치**: 방 사진 없이도 지도 기반 데이터로 릴스 광고 자동 생성

---

## 기술 스택

| 레이어 | 선택 | 비고 |
|--------|------|------|
| UI | Streamlit | Python 기반, 배포 간단 |
| 지도 데이터 | 네이버 지도 API | Static Map, 장소 검색, 도보 거리 |
| 스트리트뷰 | Playwright | 실패 시 위성지도 fallback |
| AI 카피 | OpenAI gpt-5-mini | 광고 카피, 해시태그 생성 |
| 영상 생성 | MoviePy / FFmpeg | 슬라이드쇼, 9:16, ~15초 |
| DB | SQLite → Supabase | 로컬 시작, 클라우드 확장 예정 |
| 업로드 | Instagram Graph API | MVP는 다운로드만, 추후 구현 |
| 워크플로우 | (추후) n8n | 모듈 경계가 n8n 노드 래핑에 적합하게 설계 |

---

## 프로젝트 구조

```
Gen_for_SmallBusiness/
├── app.py                        # Streamlit 진입점
├── compass/                      # 설계 문서
│   ├── context.md
│   ├── plan.md
│   └── checklist.md
├── services/
│   ├── map/
│   │   ├── __init__.py
│   │   ├── geocoding.py          # 주소 → 좌표 변환
│   │   ├── subway.py             # 근처 지하철역 + 도보 거리
│   │   └── static_map.py         # Static Map 이미지 다운로드
│   ├── street/
│   │   ├── __init__.py
│   │   └── playwright_shot.py    # 스트리트뷰 스크린샷 (실패 시 위성지도)
│   ├── ai/
│   │   ├── __init__.py
│   │   └── copy_writer.py        # gpt-5-mini 광고 카피 + 해시태그 생성
│   ├── video/
│   │   ├── __init__.py
│   │   ├── renderer.py           # MoviePy 영상 렌더링
│   │   └── templates.py          # 슬라이드 레이아웃 정의
│   └── upload/                   # 자리 예약 — MVP는 미구현
│       ├── __init__.py
│       └── instagram.py          # TODO: Instagram Graph API
├── db/
│   ├── database.py               # SQLite 연결, CRUD
│   └── models.py                 # 방 데이터 스키마
├── assets/
│   ├── fonts/                    # 한글 자막용 폰트
│   └── bgm/                      # 저작권 없는 배경음악
├── output/                       # 생성된 영상 저장
└── .env                          # API 키
```

---

## DB 스키마

```sql
CREATE TABLE rooms (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    address       TEXT NOT NULL,       -- 도로명 주소
    floor         INTEGER,             -- 층수
    size_pyeong   REAL,                -- 평수
    deposit       INTEGER,             -- 보증금 (만원)
    monthly_rent  INTEGER,             -- 월세 (만원, 전세면 0)
    options       TEXT,                -- JSON 배열 ["에어컨", "세탁기", ...]
    year_built    INTEGER,             -- 준공 연도
    lat           REAL,                -- 위도 (캐시)
    lng           REAL,                -- 경도 (캐시)
    subway_info   TEXT,                -- JSON {"station": "강남역", "walk_min": 5}
    video_path    TEXT,                -- 생성된 영상 로컬 경로
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 릴스 영상 구성 (9:16 · 1080×1920 · ~15초)

| 슬라이드 | 내용 | 시간 |
|---------|------|------|
| 1 | Static Map + 지하철역 도보 거리 오버레이 | 2초 |
| 2 | 스트리트뷰 스크린샷 (실패 시 위성지도) | 3초 |
| 3 | 방 정보 카드 (가격 · 평수 · 층 · 준공연도 · 옵션) | 3초 |
| 4 | AI 광고 카피 (후크 문장 + 특징 3줄) | 4초 |
| 5 | CTA + AI 해시태그 | 3초 |

---

## 주요 제약 및 결정 사항

### 네이버 지도 API
- Static Map: 좌표 기반 이미지 URL → 직접 다운로드 가능
- 장소 검색: 키워드로 근처 지하철역 검색 후 도보 거리 계산
- 스트리트뷰(파노라마): JS 전용 → Playwright로 스크린샷, 실패 시 위성지도 fallback
- 대중교통 경로: 유료 → MVP에서 제외, 도보 거리만 표시

### Instagram Graph API (추후)
- 비즈니스/크리에이터 계정 + Facebook 앱 심사 필요
- 영상 업로드는 공개 URL 방식 (로컬 파일 직접 불가) → S3/Cloudflare R2 임시 스토리지 필요
- **위치 태그 2개 포함**: 공인중개사 사무소 주소 + 매물 건물 주소
- MVP는 Streamlit 다운로드 버튼으로 대체

### 가격 비교 / 점수 매기기
- 경쟁 매물 크롤링 필요 → MVP 범위 외, 추후 구현

### n8n 확장
- 각 services/ 폴더가 독립 모듈로 설계됨 → HTTP Request 노드 또는 Python 실행 노드로 래핑 용이
