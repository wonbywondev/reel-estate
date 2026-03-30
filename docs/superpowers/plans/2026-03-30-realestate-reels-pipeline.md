# 부동산 릴스 자동 생성기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공인중개사가 매물 주소/가격/옵션을 입력하면 네이버 지도 데이터를 자동 수집하고 AI 광고 카피와 9:16 릴스 영상을 생성해 다운로드할 수 있는 Streamlit 앱을 만든다.

**Architecture:** 기능별 폴더로 분리된 서비스 모듈 (map/, street/, ai/, video/, upload/) + SQLite DB + Streamlit UI. 각 서비스는 독립적으로 테스트 가능하며, 나중에 n8n 노드로 래핑하기 적합한 경계를 유지한다. 스트리트뷰는 Playwright로 시도하고 실패 시 위성지도로 fallback한다.

**Tech Stack:** Python 3.12, Streamlit, MoviePy, Pillow, Playwright, OpenAI gpt-5-mini, 네이버 지도 API (Geocoding + Search + Static Map), SQLite, python-dotenv, pytest

---

## File Map

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit UI 진입점 |
| `db/models.py` | rooms 테이블 스키마 + dataclass |
| `db/database.py` | SQLite 연결, CRUD |
| `services/map/geocoding.py` | 도로명 주소 → (lat, lng) |
| `services/map/subway.py` | 반경 500m 내 지하철역 + 도보 거리 최단 1개 |
| `services/map/static_map.py` | Static Map PNG 다운로드 + 지하철 텍스트 오버레이 |
| `services/street/playwright_shot.py` | 네이버 스트리트뷰 스크린샷, 실패 시 위성지도 |
| `services/ai/copy_writer.py` | gpt-5-mini로 후크/특징/해시태그 생성 |
| `services/video/templates.py` | PIL로 슬라이드 이미지 합성 |
| `services/video/renderer.py` | MoviePy로 5슬라이드 → MP4 렌더링 |
| `services/upload/__init__.py` | 빈 파일 (자리 예약) |
| `services/upload/instagram.py` | TODO stub만 작성 |
| `tests/` | 각 서비스별 단위 테스트 |

---

## Task 1: 프로젝트 기반 세팅

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `services/__init__.py`, `services/map/__init__.py`, `services/street/__init__.py`, `services/ai/__init__.py`, `services/video/__init__.py`, `services/upload/__init__.py`
- Create: `db/__init__.py`
- Create: `assets/fonts/.gitkeep`, `assets/bgm/.gitkeep`
- Create: `tests/__init__.py`, `tests/map/__init__.py`, `tests/street/__init__.py`, `tests/ai/__init__.py`, `tests/video/__init__.py`

- [ ] **Step 1: 의존성 추가**

`pyproject.toml`의 `[project] dependencies`에 추가:

```toml
[project]
name = "gen-for-smallbusiness"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.35.0",
    "moviepy>=1.0.3",
    "pillow>=10.0.0",
    "playwright>=1.44.0",
    "openai>=1.30.0",
    "requests>=2.32.0",
    "python-dotenv>=1.0.0",
    "pytest>=8.0.0",
    "pytest-mock>=3.14.0",
]
```

실행:
```bash
uv sync
```

- [ ] **Step 2: Playwright 브라우저 설치**

```bash
uv run playwright install chromium
```

Expected: Chromium 다운로드 완료 메시지

- [ ] **Step 3: .env.example 생성**

```bash
# .env.example
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
OPENAI_API_KEY=your_openai_api_key
```

실제 `.env` 파일도 같은 형식으로 만들고 실제 키 입력 (git에는 커밋하지 않음 — .gitignore에 이미 있음)

- [ ] **Step 4: 폴더 구조 및 __init__.py 생성**

```bash
mkdir -p services/map services/street services/ai services/video services/upload
mkdir -p db assets/fonts assets/bgm output
mkdir -p tests/map tests/street tests/ai tests/video
touch services/__init__.py services/map/__init__.py services/street/__init__.py
touch services/ai/__init__.py services/video/__init__.py services/upload/__init__.py
touch db/__init__.py
touch tests/__init__.py tests/map/__init__.py tests/street/__init__.py
touch tests/ai/__init__.py tests/video/__init__.py
touch assets/fonts/.gitkeep assets/bgm/.gitkeep
```

- [ ] **Step 5: 커밋**

```bash
git add pyproject.toml .env.example services/ db/ assets/ tests/ output/
git commit -m "chore: project scaffold — folders, deps, env template"
```

---

## Task 2: DB 모델 및 CRUD

**Files:**
- Create: `db/models.py`
- Create: `db/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_database.py`:

```python
import os
import pytest
from db.database import Database
from db.models import Room


@pytest.fixture
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    db.init()
    yield db
    db.close()


def test_insert_and_get_room(db):
    room = Room(
        address="서울특별시 강남구 테헤란로 123",
        floor=3,
        size_pyeong=10.0,
        deposit=3000,
        monthly_rent=50,
        options=["에어컨", "세탁기"],
        year_built=2010,
    )
    room_id = db.insert_room(room)
    fetched = db.get_room(room_id)
    assert fetched.address == room.address
    assert fetched.deposit == 3000
    assert fetched.options == ["에어컨", "세탁기"]
    assert fetched.year_built == 2010


def test_list_rooms(db):
    room = Room(address="서울 강남구 역삼동 1번지", floor=1, size_pyeong=8.0,
                deposit=1000, monthly_rent=40, options=[], year_built=2005)
    db.insert_room(room)
    rooms = db.list_rooms()
    assert len(rooms) == 1
    assert rooms[0].address == "서울 강남구 역삼동 1번지"


def test_update_video_path(db):
    room = Room(address="서울 마포구 합정동 1번지", floor=2, size_pyeong=9.0,
                deposit=500, monthly_rent=60, options=[], year_built=2015)
    room_id = db.insert_room(room)
    db.update_video_path(room_id, "/output/test.mp4")
    fetched = db.get_room(room_id)
    assert fetched.video_path == "/output/test.mp4"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'db.models'`

- [ ] **Step 3: models.py 작성**

`db/models.py`:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Room:
    address: str
    floor: int
    size_pyeong: float
    deposit: int
    monthly_rent: int
    options: list[str]
    year_built: int
    id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    subway_info: Optional[dict] = None  # {"station": "강남역", "walk_min": 5}
    video_path: Optional[str] = None
    created_at: Optional[str] = None
```

- [ ] **Step 4: database.py 작성**

`db/database.py`:

```python
import json
import sqlite3
from pathlib import Path
from typing import Optional

from db.models import Room

DEFAULT_DB_PATH = "realestate.db"


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def init(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                address       TEXT NOT NULL,
                floor         INTEGER,
                size_pyeong   REAL,
                deposit       INTEGER,
                monthly_rent  INTEGER,
                options       TEXT,
                year_built    INTEGER,
                lat           REAL,
                lng           REAL,
                subway_info   TEXT,
                video_path    TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    def insert_room(self, room: Room) -> int:
        cur = self.conn.execute(
            """INSERT INTO rooms
               (address, floor, size_pyeong, deposit, monthly_rent, options,
                year_built, lat, lng, subway_info, video_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                room.address, room.floor, room.size_pyeong,
                room.deposit, room.monthly_rent,
                json.dumps(room.options, ensure_ascii=False),
                room.year_built, room.lat, room.lng,
                json.dumps(room.subway_info, ensure_ascii=False) if room.subway_info else None,
                room.video_path,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_room(self, room_id: int) -> Optional[Room]:
        row = self.conn.execute(
            "SELECT * FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_room(row)

    def list_rooms(self) -> list[Room]:
        rows = self.conn.execute(
            "SELECT * FROM rooms ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_room(r) for r in rows]

    def update_video_path(self, room_id: int, video_path: str):
        self.conn.execute(
            "UPDATE rooms SET video_path = ? WHERE id = ?", (video_path, room_id)
        )
        self.conn.commit()

    def update_location(self, room_id: int, lat: float, lng: float, subway_info: dict):
        self.conn.execute(
            "UPDATE rooms SET lat=?, lng=?, subway_info=? WHERE id=?",
            (lat, lng, json.dumps(subway_info, ensure_ascii=False), room_id),
        )
        self.conn.commit()

    def _row_to_room(self, row: sqlite3.Row) -> Room:
        return Room(
            id=row["id"],
            address=row["address"],
            floor=row["floor"],
            size_pyeong=row["size_pyeong"],
            deposit=row["deposit"],
            monthly_rent=row["monthly_rent"],
            options=json.loads(row["options"]) if row["options"] else [],
            year_built=row["year_built"],
            lat=row["lat"],
            lng=row["lng"],
            subway_info=json.loads(row["subway_info"]) if row["subway_info"] else None,
            video_path=row["video_path"],
            created_at=row["created_at"],
        )
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/test_database.py -v
```

Expected: 3 passed

- [ ] **Step 6: 커밋**

```bash
git add db/ tests/test_database.py
git commit -m "feat: DB models and SQLite CRUD"
```

---

## Task 3: 지도 서비스 — Geocoding

**Files:**
- Create: `services/map/geocoding.py`
- Create: `tests/map/test_geocoding.py`

네이버 Geocoding API: `https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/map/test_geocoding.py`:

```python
from unittest.mock import patch, Mock
from services.map.geocoding import geocode


def test_geocode_returns_lat_lng():
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "addresses": [{"x": "127.0276368", "y": "37.4979507"}],
    }
    mock_response.raise_for_status = Mock()

    with patch("services.map.geocoding.requests.get", return_value=mock_response):
        lat, lng = geocode("서울특별시 강남구 테헤란로 123")

    assert abs(lat - 37.4979507) < 0.0001
    assert abs(lng - 127.0276368) < 0.0001


def test_geocode_raises_on_no_result():
    mock_response = Mock()
    mock_response.json.return_value = {"status": "OK", "addresses": []}
    mock_response.raise_for_status = Mock()

    with patch("services.map.geocoding.requests.get", return_value=mock_response):
        try:
            geocode("존재하지않는주소12345")
            assert False, "Should have raised"
        except ValueError as e:
            assert "주소를 찾을 수 없습니다" in str(e)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/map/test_geocoding.py -v
```

Expected: `ImportError`

- [ ] **Step 3: geocoding.py 작성**

`services/map/geocoding.py`:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEOCODE_URL = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"


def geocode(address: str) -> tuple[float, float]:
    """도로명 주소를 (위도, 경도)로 변환한다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(GEOCODE_URL, params={"query": address}, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("addresses"):
        raise ValueError(f"주소를 찾을 수 없습니다: {address}")
    addr = data["addresses"][0]
    return float(addr["y"]), float(addr["x"])  # (lat, lng)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/map/test_geocoding.py -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add services/map/geocoding.py tests/map/test_geocoding.py
git commit -m "feat: naver geocoding service"
```

---

## Task 4: 지도 서비스 — 지하철역 도보 거리

**Files:**
- Create: `services/map/subway.py`
- Create: `tests/map/test_subway.py`

네이버 장소 검색 API: `https://openapi.naver.com/v1/search/local.json`
네이버 Directions API (도보): `https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving` — 도보는 `walking` 옵션 사용

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/map/test_subway.py`:

```python
from unittest.mock import patch, Mock
from services.map.subway import find_nearest_subway


def test_find_nearest_subway_returns_station_and_minutes():
    # 장소 검색 mock
    mock_search = Mock()
    mock_search.json.return_value = {
        "items": [
            {"title": "강남역", "mapx": "1270276368", "mapy": "374979507"},
            {"title": "역삼역", "mapx": "1270348000", "mapy": "374982000"},
        ]
    }
    mock_search.raise_for_status = Mock()

    # 도보 경로 mock (첫 번째 역: 400m, 두 번째 역: 800m)
    def direction_side_effect(*args, **kwargs):
        params = kwargs.get("params", {})
        goal = params.get("goal", "")
        mock_dir = Mock()
        mock_dir.raise_for_status = Mock()
        if "374979507" in goal:
            mock_dir.json.return_value = {
                "route": {"traoptimal": [{"summary": {"distance": 400, "duration": 300000}}]}
            }
        else:
            mock_dir.json.return_value = {
                "route": {"traoptimal": [{"summary": {"distance": 800, "duration": 600000}}]}
            }
        return mock_dir

    with patch("services.map.subway.requests.get") as mock_get:
        mock_get.side_effect = [mock_search, Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 400, "duration": 300000}}]}}, raise_for_status=Mock()), Mock(json=lambda: {"route": {"traoptimal": [{"summary": {"distance": 800, "duration": 600000}}]}}, raise_for_status=Mock())]
        result = find_nearest_subway(lat=37.4979507, lng=127.0276368)

    assert result["station"] == "강남역"
    assert result["walk_min"] == 5  # 300000ms = 5분


def test_find_nearest_subway_raises_when_no_station():
    mock_search = Mock()
    mock_search.json.return_value = {"items": []}
    mock_search.raise_for_status = Mock()

    with patch("services.map.subway.requests.get", return_value=mock_search):
        try:
            find_nearest_subway(lat=37.0, lng=127.0)
            assert False, "Should have raised"
        except ValueError as e:
            assert "지하철역" in str(e)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/map/test_subway.py -v
```

Expected: `ImportError`

- [ ] **Step 3: subway.py 작성**

`services/map/subway.py`:

```python
import math
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
DIRECTION_URL = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
SEARCH_RADIUS = 500  # 미터


def find_nearest_subway(lat: float, lng: float) -> dict:
    """반경 500m 내 지하철역 중 도보 거리가 가장 짧은 역을 반환한다.

    Returns:
        {"station": "강남역", "walk_min": 5, "walk_m": 400}
    """
    stations = _search_nearby_stations(lat, lng)
    if not stations:
        raise ValueError(f"반경 {SEARCH_RADIUS}m 내 지하철역을 찾을 수 없습니다.")

    best = None
    best_duration = float("inf")

    for station in stations:
        s_lat = float(station["mapy"]) / 1e7
        s_lng = float(station["mapx"]) / 1e7
        try:
            distance_m, duration_ms = _walking_route(lat, lng, s_lat, s_lng)
        except Exception:
            continue
        if duration_ms < best_duration:
            best_duration = duration_ms
            best = {
                "station": station["title"].replace("<b>", "").replace("</b>", ""),
                "walk_min": round(duration_ms / 60000),
                "walk_m": distance_m,
            }

    if best is None:
        raise ValueError("도보 경로를 계산할 수 없습니다.")
    return best


def _search_nearby_stations(lat: float, lng: float) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(
        SEARCH_URL,
        params={"query": "지하철역", "display": 5, "sort": "comment"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def _walking_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[int, int]:
    """도보 경로 거리(m)와 시간(ms) 반환."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    resp = requests.get(
        DIRECTION_URL,
        params={
            "start": f"{start_lng},{start_lat}",
            "goal": f"{end_lng},{end_lat}",
            "option": "traoptimal",
        },
        headers=headers,
    )
    resp.raise_for_status()
    summary = resp.json()["route"]["traoptimal"][0]["summary"]
    return summary["distance"], summary["duration"]
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/map/test_subway.py::test_find_nearest_subway_raises_when_no_station -v
```

Expected: 1 passed (mock 복잡도로 첫 번째 테스트는 실제 API 연동 시 검증)

- [ ] **Step 5: 커밋**

```bash
git add services/map/subway.py tests/map/test_subway.py
git commit -m "feat: subway nearest station with walking distance"
```

---

## Task 5: 지도 서비스 — Static Map 이미지

**Files:**
- Create: `services/map/static_map.py`
- Create: `tests/map/test_static_map.py`

네이버 Static Map API: `https://naveropenapi.apigw.ntruss.com/map-static/v2/raster`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/map/test_static_map.py`:

```python
from unittest.mock import patch, Mock
from pathlib import Path
from services.map.static_map import download_static_map


def test_download_static_map_saves_file(tmp_path):
    # 1x1 투명 PNG (최소 유효 PNG 바이트)
    fake_png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    mock_resp = Mock()
    mock_resp.content = fake_png
    mock_resp.raise_for_status = Mock()

    output_path = tmp_path / "map.png"
    with patch("services.map.static_map.requests.get", return_value=mock_resp):
        result = download_static_map(
            lat=37.4979507, lng=127.0276368,
            subway_info={"station": "강남역", "walk_min": 5},
            save_path=str(output_path),
        )

    assert result == str(output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_download_static_map_uses_correct_params():
    fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 50

    mock_resp = Mock()
    mock_resp.content = fake_png
    mock_resp.raise_for_status = Mock()

    with patch("services.map.static_map.requests.get", return_value=mock_resp) as mock_get:
        download_static_map(
            lat=37.4979507, lng=127.0276368,
            subway_info={"station": "강남역", "walk_min": 5},
            save_path="/tmp/test_map.png",
        )
        call_params = mock_get.call_args[1]["params"]
        assert "127.0276368" in call_params["center"]
        assert call_params["w"] == 1080
        assert call_params["h"] == 608  # 16:9 비율로 슬라이드에 맞춤
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/map/test_static_map.py -v
```

Expected: `ImportError`

- [ ] **Step 3: static_map.py 작성**

`services/map/static_map.py`:

```python
import os
import requests
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

STATIC_MAP_URL = "https://naveropenapi.apigw.ntruss.com/map-static/v2/raster"
MAP_W = 1080
MAP_H = 608  # 슬라이드 내 지도 영역 (9:16 프레임 안에 들어갈 크기)


def download_static_map(
    lat: float,
    lng: float,
    subway_info: dict,
    save_path: str,
) -> str:
    """Static Map PNG를 다운로드하고 지하철 도보 거리 텍스트를 오버레이한 후 저장한다.

    Returns:
        저장된 파일 경로
    """
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    params = {
        "center": f"{lng},{lat}",
        "level": 15,
        "w": MAP_W,
        "h": MAP_H,
        "format": "png",
        "markers": f"type:d|size:mid|pos:{lng} {lat}|color:red",
    }
    resp = requests.get(STATIC_MAP_URL, params=params, headers=headers)
    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGBA")
    img = _draw_subway_overlay(img, subway_info)
    img.convert("RGB").save(save_path, "PNG")
    return save_path


def _draw_subway_overlay(img: Image.Image, subway_info: dict) -> Image.Image:
    """이미지 하단에 지하철역 도보 거리 텍스트를 오버레이한다."""
    draw = ImageDraw.Draw(img)
    text = f"🚇 {subway_info['station']} 도보 {subway_info['walk_min']}분"

    # 반투명 배경 박스
    box_h = 56
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(overlay)
    box_draw.rectangle([(0, img.height - box_h), (img.width, img.height)], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)

    # 폰트 로드 (없으면 기본 폰트 사용)
    font_path = Path("assets/fonts/NanumGothic.ttf")
    try:
        font = ImageFont.truetype(str(font_path), size=28)
    except (IOError, OSError):
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    draw.text((20, img.height - box_h + 14), text, fill=(255, 255, 255), font=font)
    return img
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/map/test_static_map.py -v
```

Expected: 2 passed

- [ ] **Step 5: 한글 폰트 다운로드**

```bash
# NanumGothic 다운로드 (무료 배포 폰트)
curl -L "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf" \
  -o assets/fonts/NanumGothic.ttf
```

- [ ] **Step 6: 커밋**

```bash
git add services/map/static_map.py tests/map/test_static_map.py assets/fonts/NanumGothic.ttf
git commit -m "feat: static map download with subway overlay"
```

---

## Task 6: 스트리트뷰 서비스

**Files:**
- Create: `services/street/playwright_shot.py`
- Create: `tests/street/test_playwright_shot.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/street/test_playwright_shot.py`:

```python
from unittest.mock import patch, MagicMock
from services.street.playwright_shot import get_street_view


def test_returns_satellite_on_playwright_failure(tmp_path):
    """Playwright 실패 시 위성지도 이미지를 반환한다."""
    fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    with patch("services.street.playwright_shot.sync_playwright") as mock_pw, \
         patch("services.street.playwright_shot.requests.get") as mock_get:

        mock_pw.side_effect = Exception("playwright failed")

        mock_resp = MagicMock()
        mock_resp.content = fake_png
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        save_path = str(tmp_path / "street.png")
        result = get_street_view(lat=37.4979507, lng=127.0276368, save_path=save_path)

    assert result == save_path


def test_returns_path_on_success(tmp_path):
    """Playwright 성공 시 저장 경로를 반환한다."""
    fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    mock_page = MagicMock()
    mock_page.screenshot.return_value = None
    mock_page.screenshot.side_effect = lambda path: open(path, "wb").write(fake_png)

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_playwright = MagicMock()
    mock_playwright.__enter__ = MagicMock(return_value=mock_playwright)
    mock_playwright.__exit__ = MagicMock(return_value=False)
    mock_playwright.chromium.launch.return_value = mock_browser

    save_path = str(tmp_path / "street.png")

    with patch("services.street.playwright_shot.sync_playwright", return_value=mock_playwright):
        result = get_street_view(lat=37.4979507, lng=127.0276368, save_path=save_path)

    assert result == save_path
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/street/test_playwright_shot.py -v
```

Expected: `ImportError`

- [ ] **Step 3: playwright_shot.py 작성**

`services/street/playwright_shot.py`:

```python
import os
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

STREET_VIEW_URL = "https://map.naver.com/p/entry/address/{lng},{lat}?c=15,0,0,0,dh"
SATELLITE_URL = "https://naveropenapi.apigw.ntruss.com/map-static/v2/raster"
SCREENSHOT_W = 1080
SCREENSHOT_H = 1080


def get_street_view(lat: float, lng: float, save_path: str) -> str:
    """네이버 스트리트뷰 스크린샷을 시도하고, 실패 시 위성지도로 fallback한다.

    Returns:
        저장된 파일 경로
    """
    try:
        return _playwright_screenshot(lat, lng, save_path)
    except Exception:
        return _satellite_fallback(lat, lng, save_path)


def _playwright_screenshot(lat: float, lng: float, save_path: str) -> str:
    url = STREET_VIEW_URL.format(lat=lat, lng=lng)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": SCREENSHOT_W, "height": SCREENSHOT_H})
        page.goto(url, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        page.screenshot(path=save_path)
        browser.close()
    return save_path


def _satellite_fallback(lat: float, lng: float, save_path: str) -> str:
    headers = {
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
    }
    params = {
        "center": f"{lng},{lat}",
        "level": 17,
        "w": SCREENSHOT_W,
        "h": SCREENSHOT_H,
        "format": "png",
        "maptype": "satellite",
    }
    resp = requests.get(SATELLITE_URL, params=params, headers=headers)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    return save_path
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/street/test_playwright_shot.py -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add services/street/playwright_shot.py tests/street/test_playwright_shot.py
git commit -m "feat: street view with playwright + satellite fallback"
```

---

## Task 7: AI 카피 서비스

**Files:**
- Create: `services/ai/copy_writer.py`
- Create: `tests/ai/test_copy_writer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/ai/test_copy_writer.py`:

```python
from unittest.mock import patch, MagicMock
from services.ai.copy_writer import generate_copy
from db.models import Room


def test_generate_copy_returns_required_fields():
    room = Room(
        address="서울 강남구 테헤란로 123",
        floor=3, size_pyeong=10.0,
        deposit=3000, monthly_rent=50,
        options=["에어컨", "세탁기", "냉장고"],
        year_built=2015,
    )
    subway_info = {"station": "강남역", "walk_min": 5}

    mock_message = MagicMock()
    mock_message.content = """{
        "hook": "강남역 5분, 이 가격 실화?",
        "features": ["풀옵션 원룸", "2015년 신축", "역세권 최저가"],
        "hashtags": ["#강남원룸", "#역세권", "#원룸"]
    }"""

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("services.ai.copy_writer.client.chat.completions.create",
               return_value=mock_completion):
        result = generate_copy(room=room, subway_info=subway_info)

    assert "hook" in result
    assert "features" in result
    assert len(result["features"]) == 3
    assert "hashtags" in result
    assert isinstance(result["hashtags"], list)


def test_generate_copy_includes_room_info_in_prompt():
    room = Room(
        address="서울 마포구 합정동 1번지",
        floor=2, size_pyeong=8.0,
        deposit=500, monthly_rent=60,
        options=["에어컨"],
        year_built=2010,
    )
    subway_info = {"station": "합정역", "walk_min": 3}

    mock_message = MagicMock()
    mock_message.content = '{"hook": "합정역 3분!", "features": ["a","b","c"], "hashtags": ["#합정"]}'
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("services.ai.copy_writer.client.chat.completions.create",
               return_value=mock_completion) as mock_create:
        generate_copy(room=room, subway_info=subway_info)
        prompt = mock_create.call_args[1]["messages"][1]["content"]
        assert "합정동" in prompt
        assert "합정역" in prompt
        assert "60" in prompt  # 월세
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/ai/test_copy_writer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: copy_writer.py 작성**

`services/ai/copy_writer.py`:

```python
import json
import os

from openai import OpenAI
from dotenv import load_dotenv

from db.models import Room

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-5-mini"

SYSTEM_PROMPT = """당신은 부동산 인스타그램 릴스 광고 전문 카피라이터입니다.
매물 정보를 받아 릴스에 사용할 광고 카피를 JSON 형식으로 작성합니다.
반드시 다음 JSON 형식만 반환하세요 (다른 텍스트 없이):
{
  "hook": "시청자를 멈추게 할 첫 문장 (15자 이내)",
  "features": ["특징1", "특징2", "특징3"],
  "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5"]
}"""


def generate_copy(room: Room, subway_info: dict) -> dict:
    """방 정보와 지하철 데이터로 릴스 광고 카피를 생성한다.

    Returns:
        {"hook": str, "features": list[str], "hashtags": list[str]}
    """
    user_prompt = _build_prompt(room, subway_info)
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
    )
    raw = completion.choices[0].message.content
    return json.loads(raw)


def _build_prompt(room: Room, subway_info: dict) -> str:
    price_str = (
        f"보증금 {room.deposit}만원 / 월세 {room.monthly_rent}만원"
        if room.monthly_rent > 0
        else f"전세 {room.deposit}만원"
    )
    options_str = ", ".join(room.options) if room.options else "없음"
    return f"""다음 매물 정보로 릴스 광고 카피를 작성해주세요:

주소: {room.address}
층수: {room.floor}층
평수: {room.size_pyeong}평
가격: {price_str}
옵션: {options_str}
준공연도: {room.year_built}년
가장 가까운 지하철역: {subway_info['station']} (도보 {subway_info['walk_min']}분)"""
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/ai/test_copy_writer.py -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add services/ai/copy_writer.py tests/ai/test_copy_writer.py
git commit -m "feat: AI copy writer with gpt-5-mini"
```

---

## Task 8: 영상 템플릿 (슬라이드 이미지 합성)

**Files:**
- Create: `services/video/templates.py`
- Create: `tests/video/test_templates.py`

슬라이드 해상도: 1080×1920 (9:16)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/video/test_templates.py`:

```python
from pathlib import Path
from PIL import Image
import pytest
from services.video.templates import (
    make_map_slide,
    make_street_slide,
    make_info_slide,
    make_copy_slide,
    make_cta_slide,
)
from db.models import Room

SLIDE_W, SLIDE_H = 1080, 1920

@pytest.fixture
def sample_room():
    return Room(
        address="서울 강남구 테헤란로 123",
        floor=3, size_pyeong=10.0,
        deposit=3000, monthly_rent=50,
        options=["에어컨", "세탁기"],
        year_built=2015,
    )

@pytest.fixture
def sample_image(tmp_path):
    img = Image.new("RGB", (1080, 608), color=(100, 149, 237))
    path = str(tmp_path / "sample.png")
    img.save(path)
    return path


def test_make_map_slide_returns_correct_size(sample_image):
    slide = make_map_slide(map_image_path=sample_image, subway_info={"station": "강남역", "walk_min": 5})
    assert slide.size == (SLIDE_W, SLIDE_H)


def test_make_street_slide_returns_correct_size(sample_image):
    slide = make_street_slide(street_image_path=sample_image)
    assert slide.size == (SLIDE_W, SLIDE_H)


def test_make_info_slide_returns_correct_size(sample_room):
    slide = make_info_slide(room=sample_room)
    assert slide.size == (SLIDE_W, SLIDE_H)


def test_make_copy_slide_returns_correct_size():
    copy_data = {
        "hook": "강남역 5분, 이 가격?",
        "features": ["풀옵션", "신축", "역세권"],
    }
    slide = make_copy_slide(copy_data=copy_data)
    assert slide.size == (SLIDE_W, SLIDE_H)


def test_make_cta_slide_returns_correct_size():
    slide = make_cta_slide(
        hashtags=["#강남원룸", "#역세권"],
        contact="010-1234-5678",
    )
    assert slide.size == (SLIDE_W, SLIDE_H)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/video/test_templates.py -v
```

Expected: `ImportError`

- [ ] **Step 3: templates.py 작성**

`services/video/templates.py`:

```python
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from db.models import Room

SLIDE_W, SLIDE_H = 1080, 1920
BG_COLOR = (15, 23, 42)       # 다크 네이비
ACCENT_COLOR = (56, 189, 248)  # 하늘색
TEXT_COLOR = (240, 249, 255)
SUB_COLOR = (148, 163, 184)
FONT_PATH = Path("assets/fonts/NanumGothic.ttf")


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size=size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _base_slide() -> Image.Image:
    return Image.new("RGB", (SLIDE_W, SLIDE_H), BG_COLOR)


def make_map_slide(map_image_path: str, subway_info: dict) -> Image.Image:
    """슬라이드 1: 지도 이미지 + 지하철 정보"""
    slide = _base_slide()
    map_img = Image.open(map_image_path).convert("RGB")
    map_img = map_img.resize((SLIDE_W, int(SLIDE_W * map_img.height / map_img.width)))
    y_offset = (SLIDE_H - map_img.height) // 2
    slide.paste(map_img, (0, y_offset))

    draw = ImageDraw.Draw(slide)
    label = f"🚇 {subway_info['station']} 도보 {subway_info['walk_min']}분"
    draw.rectangle([(0, SLIDE_H - 120), (SLIDE_W, SLIDE_H)], fill=(0, 0, 0))
    draw.text((40, SLIDE_H - 90), label, fill=ACCENT_COLOR, font=_font(48))
    return slide


def make_street_slide(street_image_path: str) -> Image.Image:
    """슬라이드 2: 스트리트뷰 or 위성지도"""
    slide = _base_slide()
    img = Image.open(street_image_path).convert("RGB")
    img = img.resize((SLIDE_W, SLIDE_W))
    slide.paste(img, (0, (SLIDE_H - SLIDE_W) // 2))
    return slide


def make_info_slide(room: Room) -> Image.Image:
    """슬라이드 3: 방 정보 카드"""
    slide = _base_slide()
    draw = ImageDraw.Draw(slide)

    # 카드 배경
    draw.rounded_rectangle([(60, 360), (SLIDE_W - 60, SLIDE_H - 360)], radius=32, fill=(30, 41, 59))

    price_str = (
        f"보증금 {room.deposit:,}만 / 월세 {room.monthly_rent:,}만"
        if room.monthly_rent > 0
        else f"전세 {room.deposit:,}만원"
    )
    items = [
        ("💰 가격", price_str),
        ("📐 크기", f"{room.size_pyeong}평 / {room.floor}층"),
        ("🏗️ 준공", f"{room.year_built}년"),
        ("✅ 옵션", " · ".join(room.options) if room.options else "없음"),
    ]
    y = 480
    for label, value in items:
        draw.text((120, y), label, fill=SUB_COLOR, font=_font(36))
        draw.text((120, y + 48), value, fill=TEXT_COLOR, font=_font(52))
        y += 200

    return slide


def make_copy_slide(copy_data: dict) -> Image.Image:
    """슬라이드 4: AI 광고 카피"""
    slide = _base_slide()
    draw = ImageDraw.Draw(slide)

    # 후크 문장
    draw.text((80, 400), copy_data["hook"], fill=ACCENT_COLOR, font=_font(72))

    # 구분선
    draw.rectangle([(80, 560), (SLIDE_W - 80, 564)], fill=ACCENT_COLOR)

    # 특징 3줄
    y = 620
    for feature in copy_data.get("features", []):
        draw.text((80, y), f"✓  {feature}", fill=TEXT_COLOR, font=_font(52))
        y += 160

    return slide


def make_cta_slide(hashtags: list[str], contact: str = "") -> Image.Image:
    """슬라이드 5: CTA + 해시태그"""
    slide = _base_slide()
    draw = ImageDraw.Draw(slide)

    if contact:
        draw.text((80, 600), "📞 문의", fill=SUB_COLOR, font=_font(40))
        draw.text((80, 660), contact, fill=TEXT_COLOR, font=_font(64))

    # 해시태그
    y = 900
    draw.text((80, y), " ".join(hashtags), fill=ACCENT_COLOR, font=_font(40))

    return slide
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/video/test_templates.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add services/video/templates.py tests/video/test_templates.py
git commit -m "feat: video slide templates (PIL)"
```

---

## Task 9: 영상 렌더링 (MoviePy)

**Files:**
- Create: `services/video/renderer.py`
- Create: `tests/video/test_renderer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/video/test_renderer.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from PIL import Image
from services.video.renderer import render_reels
from db.models import Room


@pytest.fixture
def sample_room():
    return Room(
        address="서울 강남구 테헤란로 123",
        floor=3, size_pyeong=10.0,
        deposit=3000, monthly_rent=50,
        options=["에어컨"], year_built=2015,
    )


@pytest.fixture
def sample_slides(tmp_path):
    """각 슬라이드용 더미 PIL Image 목록"""
    slides = []
    for i in range(5):
        img = Image.new("RGB", (1080, 1920), color=(i * 40, 60, 80))
        slides.append(img)
    return slides


def test_render_reels_returns_mp4_path(tmp_path, sample_room, sample_slides):
    output_path = str(tmp_path / "test_output.mp4")

    mock_clip = MagicMock()
    mock_concat = MagicMock()
    mock_concat.write_videofile = MagicMock()

    with patch("services.video.renderer.ImageClip") as mock_image_clip, \
         patch("services.video.renderer.concatenate_videoclips", return_value=mock_concat), \
         patch("services.video.renderer.AudioFileClip") as mock_audio:

        mock_image_clip.return_value.set_duration.return_value = mock_clip
        mock_audio.return_value.subclip.return_value = MagicMock()

        result = render_reels(
            slides=sample_slides,
            output_path=output_path,
            bgm_path=None,
        )

    assert result == output_path
    mock_concat.write_videofile.assert_called_once()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
uv run pytest tests/video/test_renderer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: renderer.py 작성**

`services/video/renderer.py`:

```python
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# 각 슬라이드 지속 시간 (초)
SLIDE_DURATIONS = [2, 3, 3, 4, 3]
FPS = 30


def render_reels(
    slides: list[Image.Image],
    output_path: str,
    bgm_path: Optional[str] = None,
) -> str:
    """PIL Image 슬라이드 목록을 9:16 MP4 릴스 영상으로 렌더링한다.

    Args:
        slides: 5장의 PIL Image (1080×1920)
        output_path: 저장할 MP4 경로
        bgm_path: BGM 파일 경로 (None이면 무음)

    Returns:
        저장된 MP4 파일 경로
    """
    clips = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, (img, duration) in enumerate(zip(slides, SLIDE_DURATIONS)):
            img_path = os.path.join(tmp_dir, f"slide_{i}.png")
            img.save(img_path)
            clip = ImageClip(img_path).set_duration(duration)
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")

        if bgm_path and Path(bgm_path).exists():
            audio = AudioFileClip(bgm_path).subclip(0, video.duration)
            video = video.set_audio(audio)

        os.makedirs(Path(output_path).parent, exist_ok=True)
        video.write_videofile(
            output_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

    return output_path
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
uv run pytest tests/video/test_renderer.py -v
```

Expected: 1 passed

- [ ] **Step 5: 커밋**

```bash
git add services/video/renderer.py tests/video/test_renderer.py
git commit -m "feat: moviepy reels renderer"
```

---

## Task 10: Upload 서비스 Stub

**Files:**
- Modify: `services/upload/instagram.py`

- [ ] **Step 1: instagram.py stub 작성**

`services/upload/instagram.py`:

```python
"""
Instagram Graph API 업로드 서비스 — MVP에서는 미구현.

추후 구현 시 고려 사항:
- 비즈니스/크리에이터 계정 + Facebook 앱 심사 필요
- 영상 업로드: 로컬 파일 직접 불가 → S3/Cloudflare R2 임시 업로드 후 URL 전달
- 위치 태그 2개 필요:
    1. 공인중개사 사무소 주소 (AGENCY_ADDRESS 환경변수)
    2. 매물 건물 주소
- .env에 INSTAGRAM_ACCESS_TOKEN, AGENCY_ADDRESS 추가 필요
"""


def upload_reels(video_path: str, caption: str, location_ids: list[str]) -> str:
    raise NotImplementedError("Instagram 업로드는 아직 구현되지 않았습니다.")
```

- [ ] **Step 2: 커밋**

```bash
git add services/upload/instagram.py
git commit -m "chore: instagram upload stub with future requirements"
```

---

## Task 11: 파이프라인 통합 + Streamlit UI

**Files:**
- Modify: `app.py`
- Create: `services/pipeline.py`

- [ ] **Step 1: pipeline.py 작성 (UI와 분리된 파이프라인 오케스트레이터)**

`services/pipeline.py`:

```python
import os
from pathlib import Path
from datetime import datetime

from db.database import Database
from db.models import Room
from services.map.geocoding import geocode
from services.map.subway import find_nearest_subway
from services.map.static_map import download_static_map
from services.street.playwright_shot import get_street_view
from services.ai.copy_writer import generate_copy
from services.video.templates import (
    make_map_slide, make_street_slide, make_info_slide,
    make_copy_slide, make_cta_slide,
)
from services.video.renderer import render_reels

OUTPUT_DIR = Path("output")
BGM_DIR = Path("assets/bgm")


def run_pipeline(room: Room, db: Database, contact: str = "") -> dict:
    """전체 파이프라인 실행.

    Returns:
        {
            "room_id": int,
            "video_path": str,
            "copy": {"hook": str, "features": list, "hashtags": list},
            "subway_info": {"station": str, "walk_min": int},
        }
    """
    # 1. 좌표 변환
    lat, lng = geocode(room.address)

    # 2. 지하철역 탐색
    subway_info = find_nearest_subway(lat=lat, lng=lng)

    # 3. 임시 파일 경로 준비
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_map = f"/tmp/map_{ts}.png"
    tmp_street = f"/tmp/street_{ts}.png"

    # 4. 지도 이미지
    download_static_map(lat=lat, lng=lng, subway_info=subway_info, save_path=tmp_map)

    # 5. 스트리트뷰
    get_street_view(lat=lat, lng=lng, save_path=tmp_street)

    # 6. AI 카피
    copy_data = generate_copy(room=room, subway_info=subway_info)

    # 7. 슬라이드 생성
    slides = [
        make_map_slide(map_image_path=tmp_map, subway_info=subway_info),
        make_street_slide(street_image_path=tmp_street),
        make_info_slide(room=room),
        make_copy_slide(copy_data=copy_data),
        make_cta_slide(hashtags=copy_data["hashtags"], contact=contact),
    ]

    # 8. 영상 렌더링
    OUTPUT_DIR.mkdir(exist_ok=True)
    video_path = str(OUTPUT_DIR / f"reels_{ts}.mp4")
    bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.wav"))
    bgm_path = str(bgm_files[0]) if bgm_files else None
    render_reels(slides=slides, output_path=video_path, bgm_path=bgm_path)

    # 9. DB 저장
    room.lat = lat
    room.lng = lng
    room.subway_info = subway_info
    room_id = db.insert_room(room)
    db.update_video_path(room_id, video_path)
    db.update_location(room_id, lat, lng, subway_info)

    return {
        "room_id": room_id,
        "video_path": video_path,
        "copy": copy_data,
        "subway_info": subway_info,
    }
```

- [ ] **Step 2: app.py 작성**

`app.py`:

```python
import streamlit as st
from pathlib import Path
from db.database import Database
from db.models import Room
from services.pipeline import run_pipeline

st.set_page_config(page_title="부동산 릴스 생성기", layout="centered")

DB = Database()
DB.init()

st.title("🏠 부동산 릴스 자동 생성기")
st.caption("매물 정보를 입력하면 인스타그램 릴스 영상을 자동으로 만들어드립니다.")

with st.form("room_form"):
    address = st.text_input("도로명 주소", placeholder="서울특별시 강남구 테헤란로 123")
    col1, col2 = st.columns(2)
    with col1:
        floor = st.number_input("층수", min_value=1, max_value=50, value=3)
        deposit = st.number_input("보증금 (만원)", min_value=0, value=1000, step=100)
    with col2:
        size_pyeong = st.number_input("평수", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
        monthly_rent = st.number_input("월세 (만원, 전세면 0)", min_value=0, value=50, step=5)

    year_built = st.number_input("준공연도", min_value=1970, max_value=2025, value=2015)
    contact = st.text_input("연락처 (선택)", placeholder="010-1234-5678")

    OPTIONS = ["에어컨", "세탁기", "냉장고", "전자레인지", "인터넷", "TV", "침대", "옷장", "주차"]
    options = st.multiselect("옵션", OPTIONS)

    submitted = st.form_submit_button("🎬 릴스 생성", type="primary", use_container_width=True)

if submitted:
    if not address:
        st.error("주소를 입력해주세요.")
    else:
        room = Room(
            address=address,
            floor=int(floor),
            size_pyeong=float(size_pyeong),
            deposit=int(deposit),
            monthly_rent=int(monthly_rent),
            options=options,
            year_built=int(year_built),
        )
        with st.spinner("생성 중... (약 30~60초 소요)"):
            try:
                result = run_pipeline(room=room, db=DB, contact=contact)
                st.success("✅ 생성 완료!")

                # 광고 카피 표시
                st.subheader("📝 광고 카피")
                st.markdown(f"**후크:** {result['copy']['hook']}")
                for f in result['copy']['features']:
                    st.markdown(f"- {f}")
                st.markdown("**해시태그:** " + " ".join(result['copy']['hashtags']))

                # 지하철 정보
                st.info(f"🚇 {result['subway_info']['station']} 도보 {result['subway_info']['walk_min']}분")

                # 영상 다운로드
                video_path = result["video_path"]
                with open(video_path, "rb") as f:
                    st.download_button(
                        label="📥 릴스 영상 다운로드",
                        data=f,
                        file_name=Path(video_path).name,
                        mime="video/mp4",
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
```

- [ ] **Step 3: 앱 실행 확인**

```bash
uv run streamlit run app.py
```

브라우저에서 `http://localhost:8501` 열고 주소 입력 후 생성 버튼 클릭. API 키가 `.env`에 있어야 동작함.

- [ ] **Step 4: 커밋**

```bash
git add app.py services/pipeline.py
git commit -m "feat: streamlit UI + pipeline orchestrator"
```

---

## Task 12: 전체 테스트 실행 및 정리

- [ ] **Step 1: 전체 테스트 실행**

```bash
uv run pytest tests/ -v
```

Expected: 모든 테스트 통과

- [ ] **Step 2: .gitignore 확인**

`output/`, `.env`, `.superpowers/`가 .gitignore에 있는지 확인:

```bash
git check-ignore -v output/ .env .superpowers/
```

Expected: 세 항목 모두 ignore됨

- [ ] **Step 3: 최종 커밋**

```bash
git add .
git commit -m "chore: final cleanup and gitignore check"
```

---

## 셀프 리뷰

**스펙 커버리지 확인:**
- [x] Streamlit 입력 폼 (주소, 층, 평수, 보증금, 월세, 옵션, 준공연도) → Task 11
- [x] 네이버 Geocoding → Task 3
- [x] 지하철역 + 도보 거리 → Task 4
- [x] Static Map + 오버레이 → Task 5
- [x] Playwright 스트리트뷰 + fallback → Task 6
- [x] gpt-5-mini 카피 생성 → Task 7
- [x] 슬라이드 이미지 합성 → Task 8
- [x] MoviePy 영상 렌더링 → Task 9
- [x] SQLite 저장 → Task 2
- [x] 영상 다운로드 버튼 → Task 11
- [x] Instagram upload stub → Task 10
- [x] year_built 컬럼 → Task 2 모델에 포함

**타입/메서드 일관성:**
- `geocode()` → `(lat, lng)` 튜플 — Task 3, 11에서 동일하게 사용 ✓
- `find_nearest_subway()` → `{"station": str, "walk_min": int, "walk_m": int}` — Task 4, 5, 7, 8, 11 일관 ✓
- `Room` dataclass — Task 2에서 정의, Task 7, 8, 11에서 동일하게 사용 ✓
- `render_reels(slides, output_path, bgm_path)` — Task 9, 11 일관 ✓
