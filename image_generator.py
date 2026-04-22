from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

OUTPUT_FOLDER = "generated_images"

THEMES = [
    {
        "name": "dark_blue",
        "bg_top":    (26, 26, 46),
        "bg_bottom": (15, 52, 96),
        "accent":    (100, 255, 218),
        "text":      (255, 255, 255),
        "muted":     (160, 180, 200),
    },
    {
        "name": "ocean",
        "bg_top":    (15, 32, 39),
        "bg_bottom": (44, 83, 100),
        "accent":    (100, 220, 255),
        "text":      (255, 255, 255),
        "muted":     (140, 190, 210),
    },
    {
        "name": "deep_red",
        "bg_top":    (32, 1, 34),
        "bg_bottom": (111, 0, 0),
        "accent":    (255, 200, 100),
        "text":      (255, 255, 255),
        "muted":     (210, 170, 170),
    },
    {
        "name": "forest",
        "bg_top":    (1, 32, 20),
        "bg_bottom": (5, 80, 50),
        "accent":    (120, 255, 160),
        "text":      (255, 255, 255),
        "muted":     (140, 210, 170),
    },
    {
        "name": "midnight",
        "bg_top":    (10, 10, 10),
        "bg_bottom": (40, 40, 60),
        "accent":    (180, 160, 255),
        "text":      (255, 255, 255),
        "muted":     (160, 160, 200),
    },
]

LOGO_BG     = (15, 52, 96)
LOGO_ACCENT = (100, 255, 218)
LOGO_TEXT   = (255, 255, 255)


def clean_text(text: str) -> str:
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2022": "-", "\u2026": "...",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def extract_best_line(post_text: str) -> str:
    lines = [l.strip() for l in post_text.strip().split("\n") if l.strip()]
    lines = [l for l in lines if not l.startswith("#")]
    lines = [clean_text(l) for l in lines]
    if not lines:
        return "Every day is a chance to grow."
    scored = []
    total = len(lines)
    for i, line in enumerate(lines):
        if line.endswith("?"):
            continue
        if len(line) < 15 or len(line) > 80:
            continue
        position_score = i / total
        length_score   = 1 - (len(line) / 80)
        power_words    = ["don't", "never", "always", "best", "real",
                          "truth", "only", "most", "every", "stop",
                          "wake", "start", "win", "fear", "clear"]
        power_score    = sum(1 for w in power_words if w in line.lower()) * 0.2
        scored.append((position_score + length_score + power_score, line))
    if not scored:
        return lines[0][:70]
    scored.sort(reverse=True)
    return scored[0][1]


def wrap_text_to_lines(text: str, font, draw, max_width: int) -> list:
    words   = text.split()
    lines   = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_gradient_bg(draw, width, height, top_color, bottom_color):
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def draw_logo(img, draw, x, y, size):
    cx = x + size // 2
    cy = y + size // 2

    # Outer circle only — no inner ring
    border = max(6, size // 18)
    draw.ellipse(
        [(x, y), (x + size, y + size)],
        fill=LOGO_BG,
        outline=LOGO_ACCENT,
        width=border
    )

    try:
        font_file = "Roboto-VariableFont_wdth,wght.ttf"
        f_daily   = ImageFont.truetype(font_file, max(10, size // 7))
        f_ai      = ImageFont.truetype(font_file, max(22, size // 3))
        f_wisdom  = ImageFont.truetype(font_file, max(10, size // 7))
    except Exception:
        f_daily  = ImageFont.load_default()
        f_ai     = ImageFont.load_default()
        f_wisdom = ImageFont.load_default()

    # DAILY — top, safely inside
    daily_w = draw.textlength("DAILY", font=f_daily)
    draw.text(
        (cx - daily_w / 2, cy - size * 0.38),
        "DAILY",
        font=f_daily,
        fill=LOGO_ACCENT
    )

    # AI — center large
    ai_w = draw.textlength("AI", font=f_ai)
    draw.text(
        (cx - ai_w / 2, cy - size * 0.22),
        "AI",
        font=f_ai,
        fill=LOGO_ACCENT
    )

    # Divider line
    line_w = int(size * 0.55)
    line_y = int(cy + size * 0.12)
    draw.rectangle(
        [(cx - line_w // 2, line_y),
         (cx + line_w // 2, line_y + max(2, size // 60))],
        fill=LOGO_ACCENT
    )

    # WISDOM — bottom, safely inside
    wisdom_w = draw.textlength("WISDOM", font=f_wisdom)
    draw.text(
        (cx - wisdom_w / 2, cy + size * 0.19),
        "WISDOM",
        font=f_wisdom,
        fill=LOGO_TEXT
    )
def generate_card(post_text: str, theme_index: int = None) -> str:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    W, H = 1080, 1080
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    if theme_index is None:
        # Rotate by total post count — different color every post
        try:
            import json as _json
            with open("posts_log.json", "r", encoding="utf-8", errors="ignore") as f:
                posts = _json.load(f)
            theme_index = len(posts) % len(THEMES)
        except Exception:
            theme_index = datetime.now().day % len(THEMES)
    theme = THEMES[theme_index % len(THEMES)]

    draw_gradient_bg(draw, W, H, theme["bg_top"], theme["bg_bottom"])

    try:
        font_file  = "Roboto-VariableFont_wdth,wght.ttf"
        font_quote = ImageFont.truetype(font_file, 82)
        font_brand = ImageFont.truetype(font_file, 40)
        font_sub   = ImageFont.truetype(font_file, 27)
        font_tag   = ImageFont.truetype(font_file, 34)
        font_wm    = ImageFont.truetype(font_file, 27)
    except Exception:
        font_quote = ImageFont.load_default()
        font_brand = ImageFont.load_default()
        font_sub   = ImageFont.load_default()
        font_tag   = ImageFont.load_default()
        font_wm    = ImageFont.load_default()

    margin     = 80
    text_width = W - (margin * 2)

    logo_size = 210
    logo_x    = margin
    logo_y    = 60
    draw_logo(img, draw, logo_x, logo_y, logo_size)

    brand_x  = logo_x + logo_size + 28
    brand_y  = logo_y + (logo_size // 2) - 40
    draw.text((brand_x, brand_y),      "Daily AI Wisdom",   font=font_brand, fill=theme["text"])
    draw.text((brand_x, brand_y + 50), "dailyaiwisdom.com", font=font_sub,   fill=theme["muted"])

    quote  = extract_best_line(post_text)
    lines  = wrap_text_to_lines(quote, font_quote, draw, text_width)
    line_h = 100

    zone_top    = logo_y + logo_size + 60
    zone_bottom = H - 200
    zone_center = (zone_top + zone_bottom) // 2
    start_y     = zone_center - ((len(lines) * line_h) // 2)

    for i, line in enumerate(lines):
        y = start_y + (i * line_h)
        if i == len(lines) - 1:
            words = line.rsplit(" ", 1)
            if len(words) == 2:
                draw.text((margin, y), words[0] + " ", font=font_quote, fill=theme["text"])
                w1 = int(draw.textlength(words[0] + " ", font=font_quote))
                draw.text((margin + w1, y), words[1], font=font_quote, fill=theme["accent"])
            else:
                draw.text((margin, y), line, font=font_quote, fill=theme["accent"])
        else:
            draw.text((margin, y), line, font=font_quote, fill=theme["text"])

    bar_y = H - 160
    draw.rectangle(
        [(margin, bar_y), (margin + 50, bar_y + 5)],
        fill=theme["accent"]
    )
    draw.text(
        (margin, bar_y + 18),
        "#DailyAIWisdom",
        font=font_tag,
        fill=theme["muted"]
    )

    wm   = "Daily AI Wisdom"
    wm_w = int(draw.textlength(wm, font=font_wm))
    draw.text(
        (W - margin - wm_w, H - 55),
        wm,
        font=font_wm,
        fill=theme["muted"]
    )

    filename = f"post_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.png"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    img.save(filepath, "PNG")

    print(f" Image saved: {filepath}")
    return filepath


if __name__ == "__main__":
    test_post = """
You've been saying I'll start Monday for 11 Mondays.

Your competition started 11 Mondays ago.

AI doesn't wait for motivation. It works for whoever shows up.

Stop waiting to feel ready. Start today, fix it tomorrow.

What's the one thing you keep delaying that could change everything?

#DailyAIWisdom #Leadership #GrowthMindset
"""
    print("Generating all 5 theme cards...")
    for i in range(5):
        generate_card(test_post, theme_index=i)
    print("Done. Check the generated_images folder.")
