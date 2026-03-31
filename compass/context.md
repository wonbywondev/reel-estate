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
| 편의시설 검색 | 네이버 Local Search API | 대형마트/다이소/편의점 반경 검색 |
| 스트리트뷰 | Playwright | 실패 시 위성지도 fallback |
| AI 카피 | OpenAI gpt-5-mini | 광고 카피 + narrations 생성, 허위·과장 광고 금지 |
| TTS | (예정) HuggingFace mms-tts-kor | CPU 자체 호스팅 FastAPI 서버, 현재 미구현 |
| 영상 생성 | MoviePy / FFmpeg | 슬라이드쇼, 9:16, ~22초 (슬라이드 수 가변) |
| DB | SQLite → Supabase | 로컬 시작, 클라우드 확장 예정 |
| 업로드 | Instagram Graph API | MVP는 다운로드만, 추후 구현 |
| 워크플로우 | (추후) n8n | 모듈 경계가 n8n 노드 래핑에 적합하게 설계 |

---

## 프로젝트 구조

```
Gen_for_SmallBusiness/
├── app.py                        # Streamlit 진입점
├── COMPASS/                      # 설계 문서
│   ├── context.md
│   ├── plan.md
│   └── checklist.md
├── services/
│   ├── map/
│   │   ├── __init__.py
│   │   ├── geocoding.py          # 주소 → 좌표 변환
│   │   ├── nearby.py             # 근처 마트/다이소/편의점 (네이버 Local Search API)
│   │   ├── subway/               # 근처 지하철역 + 도보 거리
│   │   │   ├── __init__.py
│   │   │   ├── finder.py         # Directions API로 거리 계산, 호선별 최대 3개 반환
│   │   │   └── station_db.py     # 공공데이터 CSV 로드 + Haversine 반경 필터
│   │   └── static_map.py         # Static Map 이미지 다운로드
│   │                             # download_static_map(): level=15, 지하철 마커+오버레이
│   │                             # download_static_map_wide(): level=12, 매물 마커만
│   ├── street/
│   │   ├── __init__.py
│   │   └── playwright_shot.py    # 스트리트뷰 스크린샷 (실패 시 위성지도)
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── copy_writer.py        # gpt-5-mini 광고 카피 + narrations 생성
│   │   └── tts.py                # TTS 인터페이스 (현재 OpenAI — 403 권한 없음)
│   ├── video/
│   │   ├── __init__.py
│   │   ├── renderer.py           # MoviePy 영상 렌더링 (슬라이드별 오디오 싱크)
│   │   └── templates.py          # 슬라이드 레이아웃 정의
│   └── upload/                   # 자리 예약 — MVP는 미구현
│       ├── __init__.py
│       └── instagram.py          # TODO: Instagram Graph API
├── tts_server/                   # (예정) HuggingFace TTS 자체 호스팅 서버
│   ├── main.py                   # FastAPI POST /synthesize
│   └── model.py                  # facebook/mms-tts-kor 로드 + 추론
├── db/
│   ├── database.py               # SQLite 연결, CRUD
│   └── models.py                 # 방 데이터 스키마
├── assets/
│   ├── fonts/                    # 한글 자막용 폰트
│   ├── bgm/                      # 저작권 없는 배경음악 (미배치)
│   └── data/
│       └── subway/               # 공공데이터 CSV (서울 1~9호선, 인천, 부산)
├── output/                       # 생성된 영상 저장
└── .env                          # API 키
```

---

## DB 스키마

```sql
CREATE TABLE rooms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    address         TEXT NOT NULL,       -- 도로명 주소
    floor           INTEGER,             -- 층수
    size_pyeong     REAL,                -- 평수
    deposit         INTEGER,             -- 보증금 (만원)
    monthly_rent    INTEGER,             -- 월세 (만원, 전세면 0)
    options         TEXT,                -- JSON 배열 ["에어컨", "세탁기", ...]
    year_built      INTEGER,             -- 준공 연도
    lat             REAL,                -- 위도 (캐시)
    lng             REAL,                -- 경도 (캐시)
    subway_info     TEXT,                -- JSON [{station, walk_min, walk_m, lat, lng}, ...]
    video_path      TEXT,                -- 생성된 영상 로컬 경로
    loan_available  INTEGER DEFAULT 0,   -- 전세 대출 가능 여부
    agent_comment   TEXT,                -- 중개자 코멘트 (AI 대본 참고용)
    interior_paths  TEXT,                -- JSON 배열 [경로, ...] 실내 사진
    shops_info      TEXT,                -- JSON [{name, category, distance}, ...] 편의시설
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 릴스 영상 구성 (9:16 · 1080×1920 · 가변)

| 슬라이드 | 함수 | 내용 | 시간 |
|---------|------|------|------|
| 1 | `slide_title` | 동네 이름 (썸네일 겸용) | 2초 |
| 2 | `slide_map` | 넓은 축척 지도 (동네 위치) | 2초 |
| 3 | `slide_map` | 좁은 축척 지도 (지하철역 마커+오버레이) | 2초 |
| 4 | `slide_street` | 스트리트뷰 (실패 시 위성지도) | 3초 |
| 5~N | `slide_interior` | 실내 사진 (선택, 최대 5장) | 3초 |
| N+1 | `slide_room_info` | 방 정보 카드 (가격/평수/옵션/전세대출) | 3초 |
| N+2 | `slide_nearby_shops` | 근처 편의시설 (마트/다이소/편의점) | 3초 |
| N+3 | `slide_copy` | AI 특징 3가지 | 4초 |
| N+4 | `slide_cta` | CTA + 해시태그 | 3초 |

각 슬라이드에 하단 자막 오버레이 (AI narration 기반, TTS 구현 시 오디오 연동).

---

## 주요 제약 및 결정 사항

### 네이버 지도 API
- Static Map: 좌표 기반 이미지 다운로드, level=15(좁은)/12(넓은) 두 장 생성
- 지하철역 검색: 공공데이터 CSV 로컬 DB (서울 1~9호선, 인천, 부산) + Haversine 필터 → Directions API 실거리 계산
  - 가장 가까운 역 거리 + 500m 이내, 호선별 1개, 최대 3개 반환
- 편의시설 검색: 네이버 Local Search API (openapi.naver.com) — 지도 API와 별도 앱/키
  - 대형마트/다이소 반경 10km 최대 5개, 편의점 반경 1km 최대 1개
- 스트리트뷰: Playwright → pano_id 추출 → 전체화면 캡처, JS로 dialog 숨김 처리

### OpenAI API
- 현재 프로젝트에서 사용 가능한 모델: gpt-5-mini, gpt-5-nano, gpt-image-1-mini, text-embedding-3-small
- tts-1 접근 불가 (403) → HuggingFace TTS 서버로 대체 예정
- temperature 파라미터 미지원 (gpt-5-mini)

### TTS 계획
- facebook/mms-tts-kor (HuggingFace) — CPU 환경, GPU 없음
- FastAPI 서버 (`tts_server/`) 별도 구동 → `POST /synthesize` → MP3 bytes 반환
- `services/ai/tts.py` 인터페이스는 동일하게 유지 (save_path 반환)

### Instagram Graph API (추후)
- 비즈니스/크리에이터 계정 + Facebook 앱 심사 필요
- 영상 업로드는 공개 URL 방식 → S3/Cloudflare R2 임시 스토리지 필요
- 위치 태그 2개: 공인중개사 사무소 + 매물 건물
- MVP는 Streamlit 다운로드 버튼으로 대체

### 라이선스
- Source Available License (wonbywondev 단독 상업적 이용)
- 원본: hobi2k 작성, wonbywondev가 수정·유지

### n8n 확장
- 각 services/ 폴더가 독립 모듈로 설계됨 → HTTP Request 노드 또는 Python 실행 노드로 래핑 용이
