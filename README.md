# 부동산 릴스 자동 생성기

공인중개사가 매물 정보를 입력하면, 네이버 지도 데이터를 자동 수집하고 AI 광고 카피와 릴스 영상(MP4)을 생성해주는 로컬 실행 도구.

**타겟**: 공인중개사 (소상공인)  
**핵심 가치**: 방 사진 없이도 지도·거리뷰 데이터만으로 릴스 광고 자동 생성

---

## 주요 기능

- 주소 입력 → 좌표 자동 변환 (네이버 Geocoding API)
- 지도 2장 자동 생성 — 넓은 축척(동네) + 좁은 축척(지하철 마커)
- 스트리트뷰 자동 캡처 (Playwright, 실패 시 위성지도 fallback)
- 인근 지하철역 + 도보 거리 자동 조회 (네이버 Directions API)
- 근처 편의시설 자동 조회 — 마트/시장, 편의점, 영화관/서점, 공원
- 실내 사진 업로드 또는 즉석 카메라 촬영 (최대 5장, 슬라이드별 설명 입력)
- AI 광고 카피 + 슬라이드별 나레이션 자동 생성 (gpt-5-mini, 허위·과장 광고 금지)
- TTS 나레이션 자동 생성 (edge-tts, `ko-KR-SunHiNeural`)
- 9:16 릴스 영상 자동 합성 (MoviePy, 슬라이드별 오디오 싱크)
- 매물 정보 로컬 저장·관리 (SQLite)
- 생성된 릴스 Cloudflare R2 업로드 후 Instagram Graph API로 자동 업로드

---

## 영상 구성

9:16 · 1080×1920 · 슬라이드 수에 따라 가변 길이

| #   | 내용                                      | 시간 |
| --- | ----------------------------------------- | ---- |
| 1   | 썸네일 (주소 + 가격)                      | 2초  |
| 2   | 넓은 지도 (동네 위치)                     | 2초  |
| 3   | 거리뷰 (주변 환경)                        | 3초  |
| 4~N | 실내 사진 (선택, 최대 5장)                | 3초  |
| N+1 | 지하철역 지도 (역명 + 도보 거리)          | 3초  |
| N+2~| 근처 편의시설 (카테고리별, 해당 시 포함) | 3초  |
| -   | 방 정보 (평수/층/준공/방향/방구성/옵션)   | 3초  |
| -   | 가격 (보증금/월세/전세대출)               | 3초  |
| 끝  | CTA + 해시태그                            | 3초  |

---

## 설치 및 실행

### 사전 요건

- Python 3.12+
- ffmpeg (`brew install ffmpeg`)
- Playwright 브라우저 (`python3 -m playwright install chromium`)

### 설치

```bash
git clone <repo-url>
cd Gen_for_SmallBusiness
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```env
# 네이버 지도 API (maps.naver.com 앱)
NAVER_MAP_CLIENT_ID=...
NAVER_MAP_CLIENT_SECRET=...

# 네이버 검색 API (developers.naver.com 앱, 편의시설 검색용)
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...

# OpenAI (광고 카피 생성)
OPENAI_API_KEY=...

# TTS 음성 변경 (선택, 기본값: ko-KR-SunHiNeural)
# TTS_VOICE=ko-KR-InJoonNeural

# Cloudflare R2 (Instagram 업로드용 임시 스토리지)
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=...

# Instagram Graph API (릴스 자동 업로드)
INSTA_ACCOUNT_ID=...
INSTA_ACCESS_TOKEN=...
INSTA_GRAPH_API_TOKEN=...
```

### 실행

터미널 2개 필요:

```bash
# 터미널 1 — TTS 서버
python3 -m uvicorn tts_server.main:app --host 0.0.0.0 --port 8000

# 터미널 2 — Streamlit 앱
python3 -m streamlit run app.py
```

---

## 프로젝트 구조

```
Gen_for_SmallBusiness/
├── app.py                    # Streamlit 진입점
├── services/
│   ├── ai/
│   │   ├── copy_writer.py    # 광고 카피 + 나레이션 생성
│   │   ├── prompts.py        # 프롬프트 템플릿
│   │   └── tts.py            # TTS 서버 인터페이스
│   ├── map/
│   │   ├── geocoding.py      # 주소 → 좌표
│   │   ├── nearby.py         # 근처 편의시설 (네이버 Local Search API)
│   │   ├── static_map.py     # Static Map 이미지 다운로드 (넓은/좁은)
│   │   └── subway/           # 인근 지하철역 + 도보 거리
│   │       ├── finder.py
│   │       └── station_db.py
│   ├── street/
│   │   └── playwright_shot.py  # 스트리트뷰 캡처
│   ├── upload/
│   │   └── instagram.py      # Cloudflare R2 + Instagram Graph API 업로드
│   └── video/
│       ├── renderer.py       # MoviePy 영상 렌더링
│       └── templates.py      # 슬라이드 레이아웃
├── tts_server/
│   ├── main.py               # FastAPI POST /synthesize
│   └── model.py              # edge-tts 기반 한국어 TTS
├── db/
│   ├── database.py           # SQLite CRUD
│   └── models.py             # 데이터 스키마
├── tests/
│   ├── ai/
│   ├── db/
│   ├── map/
│   ├── street/
│   ├── upload/
│   └── video/
├── assets/
│   ├── fonts/                # 한글 자막 폰트
│   └── data/subway/          # 지하철역 공공데이터 CSV
├── output/                   # 생성된 영상 저장
└── compass/                  # 설계 문서 (context, plan, checklist)
```

---

## 기술 스택

| 레이어        | 선택                                           |
| ------------- | ---------------------------------------------- |
| UI            | Streamlit                                      |
| 지도          | 네이버 지도 API (Static Map, Directions)       |
| 편의시설      | 네이버 Local Search API                        |
| 스트리트뷰    | Playwright (Chromium)                          |
| AI 카피       | OpenAI gpt-5-mini                              |
| TTS           | edge-tts (Microsoft Azure, `ko-KR-SunHiNeural`) |
| 영상 합성     | MoviePy 2.x / FFmpeg                           |
| DB            | SQLite (로컬)                                  |
| 스토리지      | Cloudflare R2                                  |
| 인스타 업로드 | Instagram Graph API                            |

---

## 라이선스

Source Available License — wonbywondev 단독 상업적 이용 허용.  
수정·유지: wonbywondev
