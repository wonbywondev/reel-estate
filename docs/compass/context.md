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
| 편의시설 검색 | 네이버 Local Search API | 대형마트/다이소/편의점 반경 검색, region_hint로 지역 필터 |
| 스트리트뷰 | Playwright | 실패 시 위성지도 fallback |
| AI 카피 | OpenAI gpt-5-mini | 광고 카피 + narrations 생성, 허위·과장 광고 금지 |
| TTS | edge-tts (Microsoft Azure) | ko-KR-SunHiNeural, FastAPI 서버 래핑, TTS_VOICE 환경변수로 변경 가능 |
| 영상 생성 | MoviePy / FFmpeg | 슬라이드쇼, 9:16, ~22초 (슬라이드 수 가변) |
| DB | SQLite (로컬) | realestate.db, 사용자 로컬에 저장 |
| 업로드 | Instagram Graph API | INSTA_ACCOUNT_ID, INSTA_ACCESS_TOKEN, INSTA_GRAPH_API_TOKEN |
| 워크플로우 | (추후) n8n | 모듈 경계가 n8n 노드 래핑에 적합하게 설계 |

---

## 프로젝트 구조

```
Gen_for_SmallBusiness/
├── app.py                        # Streamlit 진입점
├── docs/
│   └── compass/                  # 설계 문서 (context, plan, checklist)
├── services/
│   ├── map/
│   │   ├── geocoding.py          # 주소 → 좌표 변환
│   │   ├── nearby.py             # 근처 마트/다이소/편의점 (네이버 Local Search API)
│   │   │                         # find_nearby_shops(lat, lng, region_hint="")
│   │   ├── subway/               # 근처 지하철역 + 도보 거리
│   │   │   ├── finder.py         # Directions API로 거리 계산, 호선별 최대 3개 반환
│   │   │   └── station_db.py     # 공공데이터 CSV 로드 + Haversine 반경 필터
│   │   └── static_map.py         # Static Map 이미지 다운로드
│   │                             # download_static_map(): level=15, 지하철 마커+오버레이
│   │                             # download_static_map_wide(): level=12, 매물 마커만
│   ├── street/
│   │   └── playwright_shot.py    # 스트리트뷰 스크린샷 (실패 시 위성지도)
│   ├── ai/
│   │   ├── copy_writer.py        # gpt-5-mini 광고 카피 + narrations 생성
│   │   └── tts.py                # TTS 서버 HTTP 호출 인터페이스
│   ├── video/
│   │   ├── renderer.py           # MoviePy 영상 렌더링 (슬라이드별 오디오 싱크)
│   │   └── templates.py          # 슬라이드 레이아웃 정의
│   │                             # 폰트: 에이투지체-7Bold.ttf (fallback: NanumGothic)
│   │                             # 자막: 인스타 dead zone 위 배치 (하단 380px 회피)
│   └── instagram/
│       └── uploader.py           # Instagram Graph API 릴스 업로드
├── tts_server/
│   ├── main.py                   # FastAPI POST /synthesize
│   └── model.py                  # edge-tts 기반 한국어 TTS
├── db/
│   ├── database.py               # SQLite 연결, CRUD
│   └── models.py                 # 방 데이터 스키마
├── assets/
│   ├── fonts/                    # 에이투지체 (1Thin~9Black), NanumGothic
│   ├── bgm/                      # 저작권 없는 배경음악 (미배치)
│   └── data/subway/              # 공공데이터 CSV (서울 1~9호선, 인천, 부산)
├── tests/
│   └── video/
│       └── gen_slides.py         # 슬라이드 이미지 + 대본 생성 테스트 스크립트
│                                 # (TTS 없이 이미지만, output/{slug}_{timestamp}/ 저장)
├── output/                       # 생성된 영상/이미지 저장 (로컬, .gitignore)
└── .env                          # API 키
```

---

## DB 스키마

```sql
CREATE TABLE rooms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    address         TEXT NOT NULL,
    floor           INTEGER,
    size_pyeong     REAL,
    deposit         INTEGER,
    monthly_rent    INTEGER,
    options         TEXT,                -- JSON 배열 ["에어컨", ...]
    year_built      INTEGER,
    lat             REAL,
    lng             REAL,
    subway_info     TEXT,                -- JSON [{station, walk_min, walk_m, lat, lng}, ...]
    video_path      TEXT,
    loan_available  INTEGER DEFAULT 0,
    agent_comment   TEXT,
    interior_paths  TEXT,                -- JSON 배열 [경로, ...]
    shops_info      TEXT,                -- JSON [{name, category, distance}, ...]
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

각 슬라이드에 하단 자막 오버레이 (AI narration 기반, edge-tts 오디오 연동).

---

## 주요 제약 및 결정 사항

### 네이버 지도 API
- Static Map: 좌표 기반 이미지 다운로드, level=15(좁은)/12(넓은) 두 장 생성
- 지하철역 검색: 공공데이터 CSV 로컬 DB + Haversine 필터 → Directions API 실거리 계산
  - 가장 가까운 역 거리 + 500m 이내, 호선별 1개, 최대 3개 반환
- 편의시설 검색: 네이버 Local Search API — 지도 API와 별도 앱/키
  - 쿼리에 region_hint(예: "인천 연수구") prefix를 붙여 지역 필터링
  - 대형마트/다이소 반경 10km 최대 5개, 편의점 반경 1km 최대 1개, 공원 반경 2km 최대 2개
  - ALLOWED_CATEGORIES: 슈퍼마트/종합생활용품/편의점/시장/백화점/공원만 허용
  - DISALLOWED_NAME_KEYWORDS: 상인회 등 노이즈 이름 제외
- 스트리트뷰: Playwright → pano_id 추출 → 전체화면 캡처, JS로 dialog 숨김 처리

### OpenAI API
- 사용 가능한 모델: gpt-5-mini, gpt-5-nano, gpt-image-1-mini, text-embedding-3-small
- tts-1 접근 불가 (403) → edge-tts로 전환
- temperature 파라미터 미지원 (gpt-5-mini)

### TTS
- edge-tts (Microsoft Azure, 인터넷 연결 필요)
- 기본 음성: `ko-KR-SunHiNeural` (여성), `TTS_VOICE` 환경변수로 변경
- FastAPI 서버 (`tts_server/`) — `POST /synthesize` → MP3 bytes 반환
- 모델 로드 없이 즉시 시작, torch/transformers 의존성 없음

### 슬라이드 디자인
- 폰트: 에이투지체-7Bold (fallback: NanumGothic)
- 자막 위치: 인스타그램 릴스 dead zone(하단 380px) 위에 배치
- 자막 크기: 62px

### Instagram Graph API
- API 키 발급 완료: INSTA_ACCOUNT_ID, INSTA_ACCESS_TOKEN, INSTA_GRAPH_API_TOKEN (.env 등록)
- 영상 업로드는 공개 URL 방식 → 공개 접근 가능한 임시 스토리지 필요 (ngrok 또는 S3/R2)
- 릴스 업로드 흐름: 영상 URL → 미디어 컨테이너 생성(REEL) → 게시(publish)
- 위치 태그 2개: 공인중개사 사무소 + 매물 건물 (추후)

### n8n 확장
- 각 services/ 폴더가 독립 모듈로 설계됨 → HTTP Request 노드 또는 Python 실행 노드로 래핑 용이
