"""9:16 슬라이드 이미지를 PIL로 합성한다."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

W, H = 1080, 1920
FONT_PATH = Path("assets/fonts/에이투지체-7Bold.ttf")
FONT_PATH_FALLBACK = Path("assets/fonts/NanumGothic.ttf")

# 인스타그램 릴스 dead zone (하단 버튼/텍스트 영역)
REEL_DEAD_BOTTOM = 380  # 하단 좋아요·댓글·공유 버튼 영역

# 컬러 팔레트
BG_DARK = (18, 18, 18)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
GRAY = (160, 160, 160)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (FONT_PATH, FONT_PATH_FALLBACK):
        try:
            return ImageFont.truetype(str(path), size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _base(bg_color: tuple = BG_DARK) -> Image.Image:
    return Image.new("RGB", (W, H), bg_color)


def _draw_text_centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, color=WHITE):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)


def _text_h(draw: ImageDraw.ImageDraw, font) -> int:
    """폰트 한 줄 높이 반환."""
    return int(draw.textbbox((0, 0), "가", font=font)[3])


# ---------------------------------------------------------------------------
# 공통: 이미지를 target 크기에 맞게 center-crop
# ---------------------------------------------------------------------------

def _fit_cover(src: Image.Image, tw: int, th: int) -> Image.Image:
    src_w, src_h = src.size
    scale = max(tw / src_w, th / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    src = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    return src.crop((left, top, left + tw, top + th))


# ---------------------------------------------------------------------------
# 공통: 하단 자막 오버레이 (거리뷰 등 일부 슬라이드에만 사용)
# ---------------------------------------------------------------------------

def _draw_subtitle(img: Image.Image, text: str) -> Image.Image:
    """슬라이드 하단 safe zone에 반투명 바 + 자막 텍스트를 오버레이한다."""
    if not text:
        return img

    font = _font(62)
    draw_tmp = ImageDraw.Draw(img)

    max_w = W - 80
    lines: list[str] = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw_tmp.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)

    line_h = _text_h(draw_tmp, font) + 12
    total_h = len(lines) * line_h
    bar_h = total_h + 60
    bar_top = H - REEL_DEAD_BOTTOM - bar_h

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bar = Image.new("RGBA", (W, bar_h), (0, 0, 0, 190))
    overlay.paste(bar, (0, bar_top))

    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)
    y = bar_top + (bar_h - total_h) // 2
    for line in lines:
        _draw_text_centered(draw, y, line, font, WHITE)
        y += line_h

    return img


# ---------------------------------------------------------------------------
# 슬라이드 0: 썸네일 (주소 + 가격)
# ---------------------------------------------------------------------------

def slide_title(address: str, price_str: str) -> Image.Image:
    """주소와 가격을 화면 중앙에 표시. 자막 없음."""
    img = _base()
    draw = ImageDraw.Draw(img)

    f_addr = _font(62)
    f_price = _font(88)

    # 주소 줄바꿈
    max_w = W - 120
    words = address.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=f_addr)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    addr_lh = _text_h(draw, f_addr) + 10
    price_lh = _text_h(draw, f_price) + 10
    gap = 48  # 주소·가격 사이 간격

    total_h = len(lines) * addr_lh + gap + price_lh
    y = (H - total_h) // 2

    for line in lines:
        _draw_text_centered(draw, y, line, f_addr, WHITE)
        y += addr_lh

    y += gap
    _draw_text_centered(draw, y, price_str, f_price, YELLOW)

    return img


# ---------------------------------------------------------------------------
# 슬라이드 1: Static Map
# ---------------------------------------------------------------------------

def slide_map(map_path: str, subtitle: str = "") -> Image.Image:
    """지도 이미지를 9:16 프레임에 꽉 채워 배치. 자막 없음."""
    _ = subtitle
    img = _base()
    try:
        map_img = Image.open(map_path).convert("RGB")
        img.paste(_fit_cover(map_img, W, H), (0, 0))
    except Exception:
        pass
    return img


# ---------------------------------------------------------------------------
# 슬라이드 2: 거리뷰
# ---------------------------------------------------------------------------

def slide_street(sv_path: str, subtitle: str = "") -> Image.Image:
    """거리뷰 이미지를 9:16 프레임에 꽉 채워 배치. 자막: 주소."""
    img = _base()
    try:
        sv_img = Image.open(sv_path).convert("RGB")
        img.paste(_fit_cover(sv_img, W, H), (0, 0))
    except Exception:
        pass
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드 3: 실내 사진
# ---------------------------------------------------------------------------

def slide_interior(photo_path: str, subtitle: str = "", label: str = "") -> Image.Image:
    """실내 사진을 9:16 프레임에 꽉 채워 배치. label은 하단 자막으로만 표시."""
    _ = label
    img = _base()
    try:
        photo = Image.open(photo_path).convert("RGB")
        img.paste(_fit_cover(photo, W, H), (0, 0))
    except Exception:
        pass
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드: 지하철역 지도
# ---------------------------------------------------------------------------

def slide_subway(subway_list: list[dict], map_path: str = "", subtitle: str = "") -> Image.Image:
    """지하철역 지도 이미지 + 상단 바에 역명/거리 오버레이. 하단 자막 없음."""
    _ = subtitle
    img = _base()
    if map_path:
        try:
            map_img = Image.open(map_path).convert("RGB")
            img.paste(_fit_cover(map_img, W, H), (0, 0))
        except Exception:
            pass

    if not subway_list:
        return img

    f_header = _font(54)
    f_item = _font(52)
    f_dist = _font(40)

    _d = ImageDraw.Draw(img)
    item_lh = _text_h(_d, f_item) + 8
    dist_lh = _text_h(_d, f_dist) + 8
    header_lh = _text_h(_d, f_header) + 8
    entry_gap = 24

    entries = subway_list[:3]
    content_h = (
        header_lh + 16              # 헤더
        + 2                         # 구분선
        + 20                        # 구분선 아래 패딩
        + len(entries) * (item_lh + dist_lh + entry_gap)
    )
    bar_h = content_h + 60  # 상하 패딩 30씩
    bar_top = 60

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bar = Image.new("RGBA", (W, bar_h), (0, 0, 0, 200))
    overlay.paste(bar, (0, bar_top))
    img_rgba = img.convert("RGBA")
    img = Image.alpha_composite(img_rgba, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    y = bar_top + 30

    _draw_text_centered(draw, y, "🚇 지하철역", f_header, YELLOW)
    y += header_lh + 16
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 22

    for s in entries:
        name = s["station"]
        line_name = s.get("line", "")
        walk_m = s.get("walk_m") or s.get("distance_m")
        dist_text = f"도보 {s['walk_min']}분" + (f"  {walk_m}m" if walk_m else "")
        if line_name:
            name = f"{name}  {line_name}"
        _draw_text_centered(draw, y, name, f_item, WHITE)
        y += item_lh
        _draw_text_centered(draw, y, dist_text, f_dist, GRAY)
        y += dist_lh + entry_gap

    return img


# ---------------------------------------------------------------------------
# 슬라이드: 근처 편의시설
# ---------------------------------------------------------------------------

def slide_nearby_shops(shops: list[dict], header: str = "🛒 근처 편의시설", subtitle: str = "") -> Image.Image:
    """근처 편의시설 목록을 세로 중앙에 표시. 자막 없음."""
    _ = subtitle
    img = _base()
    draw = ImageDraw.Draw(img)

    f_header = _font(64)
    f_item = _font(54)
    f_dist = _font(40)

    item_lh = _text_h(draw, f_item) + 8
    dist_lh = _text_h(draw, f_dist) + 8
    header_lh = _text_h(draw, f_header) + 8
    entry_gap = 28

    items = (shops or [])[:5]
    content_h = (
        header_lh + 20
        + 2 + 28  # 구분선
        + len(items) * (item_lh + dist_lh + entry_gap)
    )
    y = (H - content_h) // 2

    _draw_text_centered(draw, y, header, f_header, YELLOW)
    y += header_lh + 20
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 30

    if items:
        for shop in items:
            _draw_text_centered(draw, y, shop["name"], f_item, WHITE)
            y += item_lh
            _draw_text_centered(draw, y, f"{shop['distance']}m", f_dist, GRAY)
            y += dist_lh + entry_gap
    else:
        _draw_text_centered(draw, y, "정보 없음", f_item, GRAY)

    return img


# ---------------------------------------------------------------------------
# 슬라이드: 방 정보 (옵션·방향·준공·방구성)
# ---------------------------------------------------------------------------

def slide_room_options(
    floor: int,
    size_pyeong: float,
    year_built: int,
    options: list[str],
    facing: str = "",
    room_config: str = "",
    subtitle: str = "",
) -> Image.Image:
    """옵션 · 방향 · 준공연도 · 방 구성 슬라이드. 자막 없음."""
    _ = subtitle
    img = _base()
    draw = ImageDraw.Draw(img)

    f_mid = _font(56)
    f_label = _font(40)
    f_tag = _font(36)

    tag_pad, tag_gap = 22, 18
    tag_h = 54

    # --- 태그 행 계산 ---
    max_tag_w = W - 160
    rows: list[list[tuple[str, float]]] = []
    current_row: list[tuple[str, float]] = []
    current_row_w: float = 0
    for opt in options:
        bbox = draw.textbbox((0, 0), opt, font=f_tag)
        tw = float(bbox[2] - bbox[0] + tag_pad * 2)
        needed = tw if not current_row else tw + tag_gap
        if current_row and current_row_w + needed > max_tag_w:
            rows.append(current_row)
            current_row = [(opt, tw)]
            current_row_w = tw
        else:
            current_row.append((opt, tw))
            current_row_w += needed
    if current_row:
        rows.append(current_row)

    # --- 전체 높이 계산 ---
    info_lh = _text_h(draw, f_mid) + 16
    info_parts = [
        f"📐 {size_pyeong}평   {floor}층",
        f"🏗️ {year_built}년 준공",
    ]
    if facing:
        info_parts.append(f"🧭 {facing}")
    if room_config:
        info_parts.append(f"🚪 {room_config}")

    label_h = _text_h(draw, f_label) + 8
    row_block_h = tag_h + 16
    divider_gap = 20
    content_h = (
        len(info_parts) * info_lh
        + divider_gap * 2 + 2  # 구분선
        + label_h + 12
        + len(rows) * row_block_h
    )

    y = (H - content_h) // 2

    # --- 기본 정보 ---
    for d in info_parts:
        _draw_text_centered(draw, y, d, f_mid, WHITE)
        y += info_lh

    y += divider_gap
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += divider_gap + 2

    # --- 옵션 태그 ---
    _draw_text_centered(draw, y, "옵션", f_label, GRAY)
    y += label_h + 12

    for row in rows:
        row_total_w = sum(tw for _, tw in row) + tag_gap * (len(row) - 1)
        rx = int((W - row_total_w) // 2)
        for opt, tw in row:
            draw.rounded_rectangle(
                [(rx, y), (rx + int(tw), y + tag_h)],
                radius=10, outline=GRAY, width=2,
            )
            draw.text((rx + tag_pad, y + 9), opt, font=f_tag, fill=WHITE)
            rx += int(tw) + tag_gap
        y += row_block_h

    return img


# ---------------------------------------------------------------------------
# 슬라이드: 가격 + 전세대출
# ---------------------------------------------------------------------------

def slide_price(
    deposit: int,
    monthly_rent: int,
    loan_available: bool = False,
    address: str = "",
    subtitle: str = "",
) -> Image.Image:
    """가격 + 전세대출 슬라이드. 자막 없음."""
    _ = subtitle
    img = _base()
    draw = ImageDraw.Draw(img)

    f_loan = _font(52)
    f_addr = _font(34)

    lh_loan = _text_h(draw, f_loan) + 8

    # 줄 구성
    price_lines: list[tuple[str, int]] = []  # (text, font_size)
    if monthly_rent == 0:
        price_lines = [("전세", 44), (f"{deposit:,}만원", 96)]
    else:
        price_lines = [
            ("보증금", 44),
            (f"{deposit:,}만원", 96),
            ("월세", 44),
            (f"{monthly_rent}만원", 96),
        ]

    # 높이 계산
    lines_h = 0
    for _, fs in price_lines:
        lines_h += _text_h(draw, _font(fs)) + (10 if fs == 96 else 8)
    if loan_available:
        lines_h += 16 + lh_loan  # 간격 + 대출 뱃지

    y = (H - lines_h) // 2

    for text, fs in price_lines:
        f = _font(fs)
        color = YELLOW if fs == 96 else GRAY
        _draw_text_centered(draw, y, text, f, color)
        y += _text_h(draw, f) + (10 if fs == 96 else 8)

    if loan_available:
        y += 16
        _draw_text_centered(draw, y, "✅ 전세 대출 가능", f_loan, (100, 220, 100))

    if address:
        _draw_text_centered(draw, H - 120, address, f_addr, GRAY)

    return img


# ---------------------------------------------------------------------------
# 슬라이드 (구버전 호환): 방 정보 + 가격 통합
# ---------------------------------------------------------------------------

def slide_room_info(
    address: str,
    floor: int,
    size_pyeong: float,
    deposit: int,
    monthly_rent: int,
    year_built: int,
    options: list[str],
    loan_available: bool = False,
    facing: str = "",
    room_config: str = "",
    subtitle: str = "",
) -> Image.Image:
    """옵션·방향·준공연도·방구성 + 가격+전세대출 통합 카드 (구버전 호환용)."""
    img = _base()
    draw = ImageDraw.Draw(img)

    f_large = _font(72)
    f_mid = _font(52)
    f_small = _font(40)
    f_tag = _font(34)

    y = 200

    if monthly_rent == 0:
        price = f"전세  {deposit:,}만원"
    else:
        price = f"보증 {deposit:,} / 월 {monthly_rent}만원"
    _draw_text_centered(draw, y, price, f_large, YELLOW)
    y += 110

    if loan_available:
        _draw_text_centered(draw, y, "✅ 전세 대출 가능", _font(40), (100, 220, 100))
        y += 60

    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 40

    info_parts = [f"📐 {size_pyeong}평   {floor}층", f"🏗️ {year_built}년 준공"]
    if facing:
        info_parts.append(f"🧭 {facing}")
    if room_config:
        info_parts.append(f"🚪 {room_config}")
    for d in info_parts:
        _draw_text_centered(draw, y, d, f_mid)
        y += 80

    y += 20
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 40

    _draw_text_centered(draw, y, "옵션", f_small, GRAY)
    y += 60

    tag_pad, tag_gap = 20, 16
    row_x, row_y = 80, y
    for opt in options:
        bbox = draw.textbbox((0, 0), opt, font=f_tag)
        tw = bbox[2] - bbox[0] + tag_pad * 2
        if row_x + tw > W - 80:
            row_x = 80
            row_y += 60
        draw.rounded_rectangle(
            [(row_x, row_y), (row_x + tw, row_y + 50)],
            radius=10, outline=GRAY, width=2,
        )
        draw.text((row_x + tag_pad, row_y + 8), opt, font=f_tag, fill=WHITE)
        row_x += tw + tag_gap

    _draw_text_centered(draw, H - 140, address, _font(32), GRAY)
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드: AI 특징 (구버전 호환)
# ---------------------------------------------------------------------------

def slide_copy(features: list[str], subtitle: str = "") -> Image.Image:
    img = _base()
    draw = ImageDraw.Draw(img)
    f_feat = _font(60)
    y = 600
    for feat in features:
        _draw_text_centered(draw, y, f"✔  {feat}", f_feat)
        y += 120
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드: CTA + 해시태그
# ---------------------------------------------------------------------------

def slide_cta(cta: str, hashtags: list[str], subtitle: str = "") -> Image.Image:
    """CTA + 해시태그. 해시태그는 가로 흐름으로 줄바꿈."""
    _ = subtitle
    img = _base()
    draw = ImageDraw.Draw(img)

    f_cta = _font(88)
    f_hash = _font(42)

    cta_lh = _text_h(draw, f_cta) + 10
    hash_lh = _text_h(draw, f_hash) + 12

    # 해시태그 행 분리
    hash_gap = 20
    max_hash_w = W - 120
    hash_rows: list[list[str]] = []
    cur_row: list[str] = []
    cur_w = 0
    for tag in hashtags:
        tw = draw.textbbox((0, 0), tag, font=f_hash)[2]
        needed = tw if not cur_row else tw + hash_gap
        if cur_row and cur_w + needed > max_hash_w:
            hash_rows.append(cur_row)
            cur_row = [tag]
            cur_w = tw
        else:
            cur_row.append(tag)
            cur_w += needed
    if cur_row:
        hash_rows.append(cur_row)

    divider_gap = 32
    content_h = cta_lh + divider_gap + 2 + divider_gap + len(hash_rows) * hash_lh
    y = (H - content_h) // 2

    _draw_text_centered(draw, y, cta, f_cta, YELLOW)
    y += cta_lh + divider_gap
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 2 + divider_gap

    for row in hash_rows:
        row_w = sum(draw.textbbox((0, 0), t, font=f_hash)[2] for t in row) + hash_gap * (len(row) - 1)
        rx = (W - row_w) // 2
        for tag in row:
            tw = draw.textbbox((0, 0), tag, font=f_hash)[2]
            draw.text((rx, y), tag, font=f_hash, fill=GRAY)
            rx += tw + hash_gap
        y += hash_lh

    return img
