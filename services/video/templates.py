"""9:16 슬라이드 이미지를 PIL로 합성한다."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

W, H = 1080, 1920
FONT_PATH = Path("assets/fonts/NanumGothic.ttf")

# 컬러 팔레트
BG_DARK = (18, 18, 18)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
GRAY = (160, 160, 160)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _base(bg_color: tuple = BG_DARK) -> Image.Image:
    return Image.new("RGB", (W, H), bg_color)


def _draw_text_centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, color=WHITE):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)


# ---------------------------------------------------------------------------
# 공통: 이미지를 target 크기에 맞게 center-crop
# ---------------------------------------------------------------------------

def _fit_cover(src: Image.Image, tw: int, th: int) -> Image.Image:
    """이미지를 tw×th에 꽉 차도록 비율 유지 리사이즈 후 중앙 크롭한다."""
    src_w, src_h = src.size
    scale = max(tw / src_w, th / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    src = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    return src.crop((left, top, left + tw, top + th))


# ---------------------------------------------------------------------------
# 공통: 하단 자막 오버레이
# ---------------------------------------------------------------------------

def _draw_subtitle(img: Image.Image, text: str) -> Image.Image:
    """슬라이드 하단에 반투명 바 + 자막 텍스트를 오버레이한다."""
    if not text:
        return img

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bar_h = 180
    bar = Image.new("RGBA", (W, bar_h), (0, 0, 0, 180))
    overlay.paste(bar, (0, H - bar_h))

    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)
    font = _font(52)
    # 줄바꿈 처리
    max_w = W - 80
    lines: list[str] = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)

    line_h = int(draw.textbbox((0, 0), "가", font=font)[3]) + 8
    total_h = len(lines) * line_h
    y = H - bar_h + (bar_h - total_h) // 2
    for line in lines:
        _draw_text_centered(draw, y, line, font, WHITE)
        y += line_h

    return img


# ---------------------------------------------------------------------------
# 슬라이드 1: Static Map
# ---------------------------------------------------------------------------

def slide_map(map_path: str, subtitle: str = "") -> Image.Image:
    """지도 이미지를 9:16 프레임에 꽉 채워 배치한다."""
    img = _base()
    try:
        map_img = Image.open(map_path).convert("RGB")
        img.paste(_fit_cover(map_img, W, H), (0, 0))
    except Exception:
        pass
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드 2: 거리뷰
# ---------------------------------------------------------------------------

def slide_street(sv_path: str, subtitle: str = "") -> Image.Image:
    """거리뷰 이미지를 9:16 프레임에 꽉 채워 배치한다."""
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

def slide_interior(photo_path: str, subtitle: str = "") -> Image.Image:
    """실내 사진을 9:16 프레임에 꽉 채워 배치한다."""
    img = _base()
    try:
        photo = Image.open(photo_path).convert("RGB")
        img.paste(_fit_cover(photo, W, H), (0, 0))
    except Exception:
        pass
    return _draw_subtitle(img, subtitle)


# ---------------------------------------------------------------------------
# 슬라이드 4: 방 정보 카드
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
    subtitle: str = "",
) -> Image.Image:
    img = _base()
    draw = ImageDraw.Draw(img)

    f_large = _font(72)
    f_mid = _font(52)
    f_small = _font(40)
    f_tag = _font(34)

    y = 200

    # 가격
    if monthly_rent == 0:
        price = f"전세  {deposit:,}만원"
    else:
        price = f"보증 {deposit:,} / 월 {monthly_rent}만원"
    _draw_text_centered(draw, y, price, f_large, YELLOW)
    y += 110

    # 전세대출 뱃지
    if loan_available:
        badge = "✅ 전세 대출 가능"
        _draw_text_centered(draw, y, badge, _font(40), (100, 220, 100))
        y += 60

    # 구분선
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 40

    # 상세 정보
    for d in [f"📐 {size_pyeong}평   {floor}층", f"🏗️ {year_built}년 준공"]:
        _draw_text_centered(draw, y, d, f_mid)
        y += 80

    y += 20
    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 40

    # 옵션 태그
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
# 슬라이드 5: AI 특징
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
# 슬라이드 6: CTA + 해시태그
# ---------------------------------------------------------------------------

def slide_cta(cta: str, hashtags: list[str], subtitle: str = "") -> Image.Image:
    img = _base()
    draw = ImageDraw.Draw(img)

    f_cta = _font(80)
    f_hash = _font(40)

    y = 600
    _draw_text_centered(draw, y, cta, f_cta, YELLOW)
    y += 160

    draw.line([(80, y), (W - 80, y)], fill=GRAY, width=2)
    y += 60

    for tag in hashtags:
        _draw_text_centered(draw, y, tag, f_hash, GRAY)
        y += 60

    return _draw_subtitle(img, subtitle)
