from PIL import Image, ImageDraw, ImageFont
import os
import json
import random
from datetime import datetime

OUTPUT_FOLDER = "generated_images"

# Clean white design — accent color changes each post
ACCENT_COLORS = [
    (79, 70, 229),    # indigo
    (16, 185, 129),   # emerald
    (239, 68, 68),    # red
    (245, 158, 11),   # amber
    (59, 130, 246),   # blue
    (168, 85, 247),   # purple
    (236, 72, 153),   # pink
    (20, 184, 166),   # teal
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
    """Extract the best standalone line — prefers closers that work without context."""
    text  = clean_text(post_text)
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    lines = [
        l for l in lines
        if not l.startswith("#")
        and not all(c in "-=_ " for c in l)
        and not l.endswith("?")
        and 15 < len(l) < 85
        and not any(p in l.lower() for p in [
            "open claude", "type:", "prompt:", "paste your",
            "here's the", "here is the"
        ])
    ]

    if not lines:
        return "The work is the answer."

    scored = []
    total  = len(lines)
    for i, line in enumerate(lines):
        length_score = 1 - (len(line) / 85)
        power_words  = [
            "don't", "never", "always", "truth", "only",
            "stop", "disappears", "accountability", "clarity",
            "alone", "works", "myth", "control", "version",
            "insurance", "gap", "not", "real", "win"
        ]
        power_score = sum(1 for w in power_words if w in line.lower()) * 0.3

        # Closers work standalone — hooks often need context
        if i == 0:
            position_score = 0.2
        elif i >= total - 3:
            position_score = 1.6
        else:
            position_score = 0.7

        scored.append((position_score + length_score + power_score, line))

    scored.sort(reverse=True)
    return scored[0][1]


def split_last_word(text: str) -> tuple:
    """Split text into (main part, last word) for accent coloring."""
    parts = text.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return text, ""


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


def draw_logo(img, draw, x, y, size):
    cx = x + size // 2
    cy = y + size // 2

    border = max(5, size // 20)
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

    daily_w = draw.textlength("DAILY", font=f_daily)
    draw.text((cx - daily_w / 2, cy - size * 0.30), "DAILY",  font=f_daily,  fill=LOGO_ACCENT)

    ai_w = draw.textlength("AI", font=f_ai)
    draw.text((cx - ai_w / 2, cy - size * 0.14),    "AI",     font=f_ai,     fill=LOGO_ACCENT)

    line_w = int(size * 0.50)
    line_y = int(cy + size * 0.18)
    draw.rectangle(
        [(cx - line_w // 2, line_y), (cx + line_w // 2, line_y + max(2, size // 55))],
        fill=(*LOGO_ACCENT, 90)
    )

    wisdom_w = draw.textlength("WISDOM", font=f_wisdom)
    draw.text((cx - wisdom_w / 2, cy + size * 0.24), "WISDOM", font=f_wisdom, fill=LOGO_TEXT)


def generate_card(post_text: str, theme_index: int = None) -> str:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    W, H = 1080, 1080

    # White background
    img  = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Pick accent color by post count
    if theme_index is None:
        try:
            with open("posts_log.json", "r", encoding="utf-8", errors="ignore") as f:
                posts = json.load(f)
            accent_idx = len(posts) % len(ACCENT_COLORS)
        except Exception:
            accent_idx = datetime.now().day % len(ACCENT_COLORS)
    else:
        accent_idx = theme_index % len(ACCENT_COLORS)

    accent = ACCENT_COLORS[accent_idx]

    # Fonts
    try:
        font_file   = "Roboto-VariableFont_wdth,wght.ttf"
        font_quote  = ImageFont.truetype(font_file, 78)
        font_brand  = ImageFont.truetype(font_file, 38)
        font_sub    = ImageFont.truetype(font_file, 26)
        font_tag    = ImageFont.truetype(font_file, 32)
        font_wm     = ImageFont.truetype(font_file, 26)
    except Exception:
        font_quote = ImageFont.load_default()
        font_brand = ImageFont.load_default()
        font_sub   = ImageFont.load_default()
        font_tag   = ImageFont.load_default()
        font_wm    = ImageFont.load_default()

    margin     = 90
    text_width = W - (margin * 2) - 20  # leave room for side bar

    # ── Left accent bar ─────────────────────────────────
    bar_width = 10
    bar_x     = margin - 30
    # Will be drawn after we know quote height

    # ── Logo top left ────────────────────────────────────
    logo_size = 190
    logo_x    = margin
    logo_y    = 60
    draw_logo(img, draw, logo_x, logo_y, logo_size)

    # ── Brand name beside logo ────────────────────────────
    brand_x  = logo_x + logo_size + 24
    brand_y  = logo_y + (logo_size // 2) - 36
    draw.text((brand_x, brand_y),      "Daily AI Wisdom",   font=font_brand, fill=(20, 20, 20))
    draw.text((brand_x, brand_y + 48), "dailyaiwisdom.com", font=font_sub,   fill=(150, 150, 150))

    # ── Quote — extract best standalone line ─────────────
    quote = extract_best_line(post_text)

    # Wrap quote
    lines  = wrap_text_to_lines(quote, font_quote, draw, text_width)
    line_h = 96

    zone_top    = logo_y + logo_size + 80
    zone_bottom = H - 200
    zone_center = (zone_top + zone_bottom) // 2
    total_h     = len(lines) * line_h
    start_y     = zone_center - (total_h // 2)

    # Draw accent bar on left — full height of quote block
    bar_top    = start_y
    bar_bottom = start_y + total_h
    draw.rectangle(
        [(bar_x, bar_top - 10), (bar_x + bar_width, bar_bottom + 10)],
        fill=accent
    )

    # Draw quote lines — last word of last line in accent color
    text_x = margin + 10

    for i, line in enumerate(lines):
        y = start_y + (i * line_h)

        if i == len(lines) - 1:
            # Split last word — color it accent
            words = line.rsplit(" ", 1)
            if len(words) == 2 and len(words[1]) > 1:
                draw.text((text_x, y), words[0] + " ", font=font_quote, fill=(20, 20, 20))
                w1 = int(draw.textlength(words[0] + " ", font=font_quote))
                draw.text((text_x + w1, y), words[1], font=font_quote, fill=accent)
            else:
                draw.text((text_x, y), line, font=font_quote, fill=accent)
        else:
            draw.text((text_x, y), line, font=font_quote, fill=(20, 20, 20))

    # ── Accent bar bottom + hashtag ───────────────────────
    bottom_y = H - 150
    draw.rectangle(
        [(margin, bottom_y), (margin + 50, bottom_y + 6)],
        fill=accent
    )
    draw.text(
        (margin, bottom_y + 18),
        "#DailyAIWisdom",
        font=font_tag,
        fill=(150, 150, 150)
    )

    # ── Watermark bottom right ────────────────────────────
    wm   = "Daily AI Wisdom"
    wm_w = int(draw.textlength(wm, font=font_wm))
    draw.text(
        (W - margin - wm_w, H - 55),
        wm,
        font=font_wm,
        fill=(200, 200, 200)
    )

    # Save
    filename = f"post_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.png"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    img.save(filepath, "PNG")

    print(f" Image saved: {filepath}")
    return filepath


if __name__ == "__main__":
    test_post = """The meeting had 14 people. Three were actually needed.
The other eleven showed up to look involved.
33 hours a month of human attention used to prevent someone asking why weren't you there.
Open Claude. Paste your last 5 meeting invites. Ask who actually had to be there.
Watch the number of invites you send next week drop by 60%.
The meeting isn't about communication. It's about insurance against accountability.
What would you do with six full days back?
#DailyAIWisdom #Leadership #WorkLife"""

    print("Generating test cards...")
    for i in range(8):
        generate_card(test_post, theme_index=i)
    print("Done. Check generated_images folder.")