#!/usr/bin/env python3
"""Generate the local PNG marks used by the character selector."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
HERO_DIR = ROOT / "assets" / "heroes"
BRAND_DIR = ROOT / "assets" / "brand"
WORK_SIZE = 1024
OUTPUT_SIZE = 256


def save_icon(image: Image.Image, name: str) -> None:
    image.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.LANCZOS).save(
        HERO_DIR / name, "PNG", optimize=True
    )


def star_points(cx: float, cy: float, outer: float, inner: float, count: int = 5) -> list[tuple[float, float]]:
    points = []
    for index in range(count * 2):
        angle = -math.pi / 2 + index * math.pi / count
        radius = outer if index % 2 == 0 else inner
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def ironman() -> Image.Image:
    image = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    red = "#b51f2e"
    dark = "#5f111a"
    gold = "#f4bb3f"
    gold_dark = "#b77916"
    cyan = "#bdf8ff"
    outer = [(292, 92), (732, 92), (844, 222), (808, 722), (658, 902), (366, 902), (216, 722), (180, 222)]
    draw.polygon(outer, fill=red, outline=dark, width=34)
    draw.polygon([(292, 164), (732, 164), (776, 280), (708, 744), (612, 834), (412, 834), (316, 744), (248, 280)], fill=gold, outline=gold_dark, width=26)
    draw.polygon([(248, 280), (356, 224), (668, 224), (776, 280), (708, 396), (316, 396)], fill="#e4a62c")
    draw.polygon([(316, 396), (708, 396), (665, 704), (582, 782), (442, 782), (359, 704)], fill="#f7c94f")
    draw.polygon([(304, 416), (468, 438), (430, 508), (298, 476)], fill=cyan, outline="#3b7181", width=18)
    draw.polygon([(720, 416), (556, 438), (594, 508), (726, 476)], fill=cyan, outline="#3b7181", width=18)
    draw.line([(422, 665), (512, 692), (602, 665)], fill=gold_dark, width=22)
    draw.polygon([(180, 222), (292, 92), (314, 240), (248, 280)], fill="#d3373f")
    draw.polygon([(844, 222), (732, 92), (710, 240), (776, 280)], fill="#d3373f")
    return image


def thor() -> Image.Image:
    image = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    electric = "#6fd8ff"
    for points in (
        [(162, 640), (310, 504), (258, 504), (420, 330)],
        [(800, 734), (700, 602), (756, 602), (622, 450)],
        [(214, 288), (340, 380), (310, 394), (432, 514)],
    ):
        draw.line(points, fill=electric, width=32, joint="curve")
        draw.line(points, fill="#e5fbff", width=10, joint="curve")
    draw.rounded_rectangle((426, 394, 594, 900), radius=58, fill="#754528", outline="#2f201b", width=30)
    for y in range(454, 832, 72):
        draw.line((438, y, 582, y + 44), fill="#c28b57", width=25)
    draw.rounded_rectangle((142, 164, 882, 480), radius=72, fill="#aebdca", outline="#334756", width=36)
    draw.polygon([(184, 214), (320, 214), (260, 430), (174, 430)], fill="#dbe4eb")
    draw.polygon([(704, 214), (840, 214), (850, 430), (764, 430)], fill="#7f94a5")
    draw.line((320, 260, 704, 260), fill="#eef5f8", width=24)
    draw.ellipse((458, 834, 562, 938), fill="#aebdca", outline="#334756", width=26)
    return image


def captain_america() -> Image.Image:
    image = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    bounds = (88, 88, 936, 936)
    draw.ellipse(bounds, fill="#c92838", outline="#67131d", width=30)
    draw.ellipse((186, 186, 838, 838), fill="#f4f5f7", outline="#d2d7df", width=12)
    draw.ellipse((278, 278, 746, 746), fill="#c92838")
    draw.ellipse((374, 374, 650, 650), fill="#2353a4", outline="#17366b", width=20)
    draw.polygon(star_points(512, 512, 116, 49), fill="white", outline="#d9e7ff")
    draw.arc((112, 112, 912, 912), 198, 325, fill="#ff6670", width=22)
    return image


def hulk() -> Image.Image:
    image = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    green = "#68bd45"
    light = "#8bd45c"
    dark = "#285b27"
    draw.rounded_rectangle((338, 574, 690, 946), radius=92, fill=green, outline=dark, width=30)
    fingers = [(170, 280, 344, 650), (322, 172, 492, 608), (474, 142, 646, 608), (626, 230, 800, 646)]
    for index, box in enumerate(fingers):
        draw.rounded_rectangle(box, radius=78, fill=light if index in (1, 2) else green, outline=dark, width=28)
        draw.arc((box[0] + 28, box[1] + 24, box[2] - 28, box[1] + 154), 198, 344, fill="#b6ed87", width=16)
    draw.rounded_rectangle((202, 522, 818, 790), radius=112, fill=green, outline=dark, width=32)
    draw.polygon([(746, 516), (894, 572), (842, 772), (658, 764), (598, 670)], fill=green, outline=dark)
    draw.line([(746, 516), (894, 572), (842, 772), (658, 764)], fill=dark, width=30, joint="curve")
    draw.line((288, 624, 716, 624), fill="#4a922f", width=22)
    draw.line((362, 776, 680, 776), fill="#4a922f", width=22)
    return image


def spiderman() -> Image.Image:
    image = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((154, 70, 870, 954), fill="#d52b3a", outline="#5d111b", width=34)
    center = (512, 470)
    for target in ((512, 94), (710, 140), (842, 320), (854, 570), (730, 822), (512, 934), (294, 822), (170, 570), (182, 320), (314, 140)):
        draw.line((center, target), fill="#391017", width=18)
    for inset in (128, 214, 300):
        draw.arc((154 + inset // 2, 70 + inset, 870 - inset // 2, 954 - inset), 184, 356, fill="#391017", width=16)
        draw.arc((154 + inset // 2, 70 + inset, 870 - inset // 2, 954 - inset), 4, 176, fill="#391017", width=16)
    left_eye = [(286, 342), (454, 414), (420, 650), (248, 550)]
    right_eye = [(738, 342), (570, 414), (604, 650), (776, 550)]
    draw.polygon(left_eye, fill="white", outline="#151419")
    draw.line(left_eye + [left_eye[0]], fill="#151419", width=30, joint="curve")
    draw.polygon(right_eye, fill="white", outline="#151419")
    draw.line(right_eye + [right_eye[0]], fill="#151419", width=30, joint="curve")
    return image


def marvel_wordmark() -> None:
    width, height = 1280, 480
    image = Image.new("RGB", (width, height), "#ed1d24")
    font = ImageFont.truetype("/usr/share/fonts/X11/Type1/NimbusSansNarrow-Bold.pfb", 410)
    mask = Image.new("L", (1600, 600), 0)
    mask_draw = ImageDraw.Draw(mask)
    box = mask_draw.textbbox((0, 0), "MARVEL", font=font, stroke_width=2)
    mask_draw.text((-box[0], -box[1]), "MARVEL", font=font, fill=255, stroke_width=2)
    crop = mask.crop(mask.getbbox())
    crop.thumbnail((1160, 370), Image.Resampling.LANCZOS)
    x = (width - crop.width) // 2
    y = (height - crop.height) // 2
    image.paste("white", (x, y), crop)
    image.resize((640, 240), Image.Resampling.LANCZOS).save(
        BRAND_DIR / "marvel.png", "PNG", optimize=True
    )


def main() -> None:
    HERO_DIR.mkdir(parents=True, exist_ok=True)
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    save_icon(ironman(), "ironman.png")
    save_icon(thor(), "thor.png")
    save_icon(captain_america(), "capitan-america.png")
    save_icon(hulk(), "hulk.png")
    save_icon(spiderman(), "spiderman.png")
    marvel_wordmark()
    print("Creati 5 loghi personaggio e il wordmark Marvel.")


if __name__ == "__main__":
    main()
