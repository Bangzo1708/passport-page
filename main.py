#!/usr/bin/env python3
"""
The Passport Page of a Country That Isn't There.

Writes one image to /output/entry.png: an open passport spread of the
invented Republic of Zalissia -- a landlocked steppe republic between
Borovnya (west) and the Tarkhan Khanate (east).

Everything is drawn programmatically with Pillow. No network, no external
assets, no randomness beyond a fixed seed, so the output is deterministic.

Document timeline (all stamps after the date of issue):
  - Passport issued .......... 12 FEB 2024, Zalissk (valid to 12 FEB 2034)
  - Holder ................... Mara Illyna Koval, b. 14 MAR 1988, Zalissk
  - Trip 1 (trade, March) .... exit Zalissia 03 MAR 2024 -> enter Borovnya
                               (Drovsk) 03 MAR 2024 -> exit Borovnya
                               21 MAR 2024 -> enter Zalissia 21 MAR 2024
  - Visa ..................... Tarkhan Khanate business visa No. 0441,
                               issued 02 JUN 2024, valid 02 JUN-30 SEP 2024
  - Trip 2 (trade, June) ..... exit Zalissia 09 JUN 2024 (+ transit fee
                               40 ZAL paid) -> enter Khanate (Qarashahr)
                               10 JUN 2024 -> exit Khanate 28 JUN 2024
                               -> enter Zalissia 29 JUN 2024
  - Telling paperwork detail . the Khanate visa condition:
                               "TRADE IN WOOL AND AMBER ONLY.
                                EMPLOYMENT PROHIBITED."
                               plus the trilingual data page
                               (Zalissian / Russian / English), which
                               marks Zalissia as a borderland caught
                               between two larger neighbours.
"""

import math
import os
import random
import stat

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Canvas and palette
# --------------------------------------------------------------------------

W, H = 1024, 1024
OUT = "/output/entry.png"

DESK = (38, 41, 46)            # dark slate desk
DESK_LIGHT = (52, 56, 62)
PAGE = (244, 239, 227)         # cream paper
PAGE_RIGHT = (246, 241, 229)
INK = (28, 43, 30)             # dark green-black print ink
INK_SOFT = (74, 82, 70)
RULE = (150, 138, 110)
GOLD = (138, 109, 47)
GREEN = (31, 77, 46)           # Zalissian green
STAMP_BLUE = (38, 74, 143)
STAMP_PURPLE = (104, 63, 150)
STAMP_RED = (163, 44, 44)
VISA_GREEN = (31, 77, 46)
MRZ_BAND = (232, 226, 210)

RNG = random.Random(20261121)  # fixed seed: deterministic speckles

# --------------------------------------------------------------------------
# Fonts (DejaVu ships with most Linux images; fall back gracefully)
# --------------------------------------------------------------------------

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype",
]


def _find_font(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


_SANS = _find_font(["DejaVuSans.ttf", "LiberationSans-Regular.ttf",
                    "NotoSans-Regular.ttf"])
_SANS_B = _find_font(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                      "NotoSans-Bold.ttf"])
_SERIF = _find_font(["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"])
_SERIF_B = _find_font(["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"])
_MONO = _find_font(["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",
                    "NotoSansMono-Regular.ttf"])


def font(size, bold=False, mono=False, serif=False):
    path = _MONO if mono else _SERIF_B if (serif and bold) else \
        _SERIF if serif else _SANS_B if bold else _SANS
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    # Pillow's built-in default font honours size on Pillow >= 9.2.
    return ImageFont.load_default(size)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(draw, cx, y, text, fnt, fill=INK):
    w, _ = text_size(draw, text, fnt)
    draw.text((cx - w / 2, y), text, font=fnt, fill=fill)


# --------------------------------------------------------------------------
# ICAO 9303 machine-readable zone
# --------------------------------------------------------------------------

_MRZ_VALUES = {chr(ord("0") + i): i for i in range(10)}
_MRZ_VALUES.update({chr(ord("A") + i): 10 + i for i in range(26)})
_MRZ_VALUES["<"] = 0


def mrz_check(field):
    total = 0
    for i, ch in enumerate(field):
        total += _MRZ_VALUES[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def build_mrz():
    line1 = "P<ZAL" + "KOVAL<<MARA<ILLYNA"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "ZA8472913"
    dob = "880314"
    exp = "340212"
    personal = "<" * 14
    line2 = (doc + mrz_check(doc) + "ZAL" + dob + mrz_check(dob) + "F"
             + exp + mrz_check(exp) + personal + mrz_check(personal))
    line2 = line2 + mrz_check(line2)
    assert len(line1) == 44 and len(line2) == 44
    return line1, line2


# --------------------------------------------------------------------------
# Small drawn elements
# --------------------------------------------------------------------------

def draw_emblem(size=72):
    """Zalissian arms: a gold-rimmed green shield, a white pine, one star."""
    w, h = size, int(size * 1.08)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = w // 2
    # shield outline (gold) and field (green)
    pts = [(4, 6), (w - 4, 6), (w - 4, h // 2), (cx, h - 4), (4, h // 2)]
    d.polygon(pts, fill=GREEN + (255,), outline=GOLD + (255,))
    d.line(pts + [pts[0]], fill=GOLD + (255,), width=3)
    # pine tree: three stacked triangles + trunk, in paper white
    def tri(y0, y1, half):
        d.polygon([(cx, y0), (cx - half, y1), (cx + half, y1)],
                  fill=(244, 239, 227, 255))
    tri(h // 4 - 4, h // 4 + 16, 10)
    tri(h // 4 + 8, h // 4 + 28, 14)
    tri(h // 4 + 20, h // 4 + 40, 18)
    d.rectangle([cx - 3, h // 4 + 40, cx + 3, h // 4 + 50],
                fill=(244, 239, 227, 255))
    # single gold star above the pine
    sx, sy, r = cx, h // 4 - 12, 7
    star = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        star.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
    d.polygon(star, fill=GOLD + (255,))
    return img


def draw_portrait(w=140, h=176):
    """Passport photo of Mara Illyna Koval: dark braid, embroidered collar,
    flat documentary style on a pale blue-grey backdrop."""
    img = Image.new("RGB", (w, h), (196, 206, 212))
    d = ImageDraw.Draw(img)
    # backdrop gradient
    for y in range(h):
        t = y / max(h - 1, 1)
        col = tuple(int(a + (b - a) * t) for a, b in
                    zip((206, 214, 219), (172, 184, 192)))
        d.line([(0, y), (w, y)], fill=col)
    cx = w // 2
    skin = (230, 189, 147)
    skin_dark = (214, 168, 124)
    hair = (74, 50, 38)
    # hair mass behind the head
    d.ellipse([cx - 38, 14, cx + 38, 96], fill=hair)
    # shoulders / jacket (dark green) and white blouse
    d.polygon([(0, h), (0, 148), (52, 132), (88, 132), (w, 148), (w, h)],
              fill=(46, 74, 56))
    d.polygon([(52, 132), (88, 132), (cx, 168), (cx - 14, 168)],
              fill=(245, 243, 236))
    # red folk-embroidery band along the collar (small diamonds)
    for i, x in enumerate(range(56, 86, 6)):
        d.polygon([(x, 140), (x + 3, 136), (x + 6, 140), (x + 3, 144)],
                  fill=(168, 52, 44) if i % 2 == 0 else (31, 77, 46))
    # neck
    d.rectangle([cx - 11, 118, cx + 11, 140], fill=skin)
    d.rectangle([cx - 11, 118, cx + 11, 124], fill=skin_dark)
    # braid over her right shoulder (viewer left), tucked inside the frame
    bx = 40
    for i, (yy, rr) in enumerate([(134, 8), (146, 9), (158, 9), (170, 7)]):
        d.ellipse([bx - rr, yy - rr, bx + rr, yy + rr], fill=hair)
        d.arc([bx - rr + 2, yy - rr + 2, bx + rr - 2, yy + rr - 2],
              200, 340, fill=(110, 80, 60), width=1)
    # small red tie where the braid leaves the hair
    d.rectangle([bx - 7, 126, bx + 7, 131], fill=(168, 52, 44))
    # face
    d.ellipse([cx - 33, 34, cx + 33, 122], fill=skin)
    # ears
    d.ellipse([cx - 37, 70, cx - 29, 88], fill=skin)
    d.ellipse([cx + 29, 70, cx + 37, 88], fill=skin)
    # hair framing the face, centre parting
    d.pieslice([cx - 36, 26, cx + 36, 96], 180, 360, fill=hair)
    d.polygon([(cx - 34, 66), (cx - 30, 30), (cx - 18, 52), (cx - 24, 78)],
              fill=hair)
    d.polygon([(cx + 34, 66), (cx + 30, 30), (cx + 18, 52), (cx + 24, 78)],
              fill=hair)
    # brows
    d.line([(cx - 24, 66), (cx - 10, 63)], fill=hair, width=3)
    d.line([(cx + 10, 63), (cx + 24, 66)], fill=hair, width=3)
    # eyes
    for ex in (cx - 17, cx + 17):
        d.ellipse([ex - 7, 70, ex + 7, 79], fill=(250, 248, 244))
        d.ellipse([ex - 4, 71, ex + 4, 79], fill=(58, 44, 34))
        d.ellipse([ex - 2, 73, ex + 2, 77], fill=(16, 12, 10))
        d.line([(ex - 8, 70), (ex + 8, 70)], fill=hair, width=2)
    # nose and mouth
    d.line([(cx, 78), (cx - 2, 94), (cx + 3, 96)], fill=skin_dark, width=2)
    d.line([(cx - 8, 106), (cx + 8, 106)], fill=(164, 96, 84), width=3)
    d.line([(cx - 6, 108), (cx + 6, 108)], fill=(188, 128, 112), width=1)
    # soft cheek shading
    d.ellipse([cx - 30, 88, cx - 16, 100], fill=(226, 172, 138))
    d.ellipse([cx + 16, 88, cx + 30, 100], fill=(226, 172, 138))
    # thin photo border
    d.rectangle([0, 0, w - 1, h - 1], outline=(120, 128, 134), width=1)
    return img


def draw_signature(draw, x, y, scale=1.0):
    """A quick ink signature: 'M. Koval' in one flowing stroke."""
    pts = [(0, 8), (6, 0), (12, 10), (18, 2), (24, 9), (30, 4), (38, 8),
           (46, 2), (54, 10), (62, 3), (70, 8), (78, 5)]
    pts = [(x + px * scale, y + py * scale) for px, py in pts]
    draw.line(pts, fill=INK, width=2, joint="curve")
    draw.line([(x + 84 * scale, y + 2 * scale),
               (x + 96 * scale, y + 9 * scale)], fill=INK, width=2)


# --------------------------------------------------------------------------
# Ink stamps (drawn on their own layer, then rotated and pasted)
# --------------------------------------------------------------------------

def make_stamp(country, kind, place, date, color, w=216, h=88):
    """A rectangular border stamp: country / ENTRY or EXIT / place / date."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = color + (235,)
    d.rounded_rectangle([3, 3, w - 4, h - 4], radius=8, outline=ink, width=3)
    d.rounded_rectangle([8, 8, w - 9, h - 9], radius=5, outline=ink, width=1)
    f_country = font(15, bold=True)
    f_kind = font(13, bold=True)
    f_small = font(11)
    f_date = font(13, bold=True)
    draw_centered(d, w // 2, 13, country, f_country, fill=ink)
    draw_centered(d, w // 2, 32, kind, f_kind, fill=ink)
    draw_centered(d, w // 2, 50, place, f_small, fill=ink)
    draw_centered(d, w // 2, 66, date, f_date, fill=ink)
    # tiny star in each top corner
    for sx in (16, w - 16):
        d.text((sx - 4, 12), "*", font=font(11, bold=True), fill=ink)
    return layer


def paste_stamp(base, stamp, cx, cy, angle):
    rotated = stamp.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.paste(rotated, (int(cx - rotated.width / 2),
                         int(cy - rotated.height / 2)), rotated)


def make_fee_stamp(text, date, color=STAMP_RED, w=250, h=62):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = color + (235,)
    d.rounded_rectangle([3, 3, w - 4, h - 4], radius=6, outline=ink, width=3)
    draw_centered(d, w // 2, 10, text, font(14, bold=True), fill=ink)
    draw_centered(d, w // 2, 32, date, font(13, bold=True), fill=ink)
    return layer


# --------------------------------------------------------------------------
# Page builders
# --------------------------------------------------------------------------

def guilloche(draw, x0, y0, x1, y1, color=(226, 220, 202), step=18):
    """Faint wavy security lines across a page region."""
    for yy in range(y0, y1, step):
        pts = []
        for x in range(x0, x1 + 1, 8):
            pts.append((x, yy + 2 * math.sin((x - x0) / 26.0)))
        draw.line(pts, fill=color, width=1)


def field(draw, x, y, label, value, label_f, value_f, width=200):
    draw.text((x, y), label, font=label_f, fill=INK_SOFT)
    draw.text((x, y + 15), value, font=value_f, fill=INK)


def build_data_page():
    """Left page: the biographical data page with portrait and MRZ."""
    pg = Image.new("RGB", (490, 696), PAGE)
    d = ImageDraw.Draw(pg, "RGBA")
    guilloche(d, 14, 180, 476, 610)
    # cover edge
    d.rectangle([0, 0, 489, 695], outline=(120, 104, 74), width=2)

    lx = 0
    # emblem and country name
    emblem = draw_emblem(66)
    pg.paste(emblem, (245 - emblem.width // 2, 16), emblem)
    draw_centered(d, 245, 96, "REPUBLIC OF ZALISSIA",
                  font(20, serif=True, bold=True))
    draw_centered(d, 245, 122, "РЕСПУБЛИКА ЗАЛИССИЯ", font(12))
    draw_centered(d, 245, 142, "PASSPORT  ·  ПАСПОРТ", font(13, bold=True))
    d.line([(26, 166), (464, 166)], fill=RULE, width=1)
    d.line([(26, 170), (464, 170)], fill=RULE, width=2)

    # portrait, top left
    photo = draw_portrait(140, 176)
    pg.paste(photo, (26, 184))
    # small embossed seal overlapping the photo's lower right corner
    seal = Image.new("RGBA", (54, 54), (0, 0, 0, 0))
    sd = ImageDraw.Draw(seal)
    sd.ellipse([2, 2, 51, 51], outline=GREEN + (220,), width=2)
    sd.ellipse([8, 8, 45, 45], outline=GREEN + (220,), width=1)
    sd.text((21, 18), "*", font=font(16, bold=True), fill=GREEN + (220,))
    pg.paste(seal, (26 + 140 - 40, 184 + 176 - 40), seal)

    # type / code / number, right of the photo
    fx = 186
    lab_f, val_f = font(11), font(15, bold=True)
    field(d, fx, 184, "Type / Тип", "P", lab_f, val_f)
    field(d, fx + 62, 184, "Code / Код", "ZAL", lab_f, val_f)
    field(d, fx + 128, 184, "Passport No. / №", "ZA8472913", lab_f, val_f)
    field(d, fx, 236, "Surname / Фамилия", "KOVAL", lab_f, font(17, bold=True))
    field(d, fx, 288, "Given names / Имя", "MARA ILLYNA", lab_f,
          font(17, bold=True))

    # data grid below the photo
    gy = 380
    field(d, 26, gy, "Nationality / Гражданство", "ZALISSIAN", lab_f, val_f)
    field(d, 268, gy, "Sex / Пол", "F", lab_f, val_f)
    field(d, 26, gy + 52, "Date of birth / Дата рожд.", "14 MAR 1988",
          lab_f, val_f)
    field(d, 268, gy + 52, "Place of birth / Место рожд.", "ZALISSK",
          lab_f, val_f)
    field(d, 26, gy + 104, "Date of issue / Дата выдачи", "12 FEB 2024",
          lab_f, val_f)
    field(d, 268, gy + 104, "Date of expiry / Действ. до", "12 FEB 2034",
          lab_f, val_f)
    field(d, 26, gy + 156, "Authority / Кем выдан",
          "MINISTRY OF THE INTERIOR — ZALISSK", lab_f, font(13, bold=True))

    # holder's signature
    d.text((26, gy + 200), "Holder's signature / Подпись",
           font=lab_f, fill=INK_SOFT)
    draw_signature(d, 30, gy + 216)
    d.line([(26, gy + 232), (220, gy + 232)], fill=RULE, width=1)

    # machine-readable zone
    d.rectangle([14, 648, 476, 684], fill=MRZ_BAND)
    mrz1, mrz2 = build_mrz()
    mrz_f = font(14, mono=True)
    d.text((22, 652), mrz1, font=mrz_f, fill=INK)
    d.text((22, 670), mrz2, font=mrz_f, fill=INK)
    return pg


def build_visa_page():
    """Right page: the Khanate business visa, eight border stamps and the
    paid transit-fee stamp -- one coherent travel history."""
    pg = Image.new("RGB", (490, 696), PAGE_RIGHT)
    d = ImageDraw.Draw(pg, "RGBA")
    guilloche(d, 14, 220, 476, 640)
    d.rectangle([0, 0, 489, 695], outline=(120, 104, 74), width=2)

    # header
    d.text((26, 20), "VISAS", font=font(13, bold=True), fill=INK)
    d.text((26, 38), "ВИЗЫ", font=font(11), fill=INK_SOFT)
    d.text((448, 20), "12", font=font(13, bold=True), fill=INK)
    d.line([(26, 58), (464, 58)], fill=RULE, width=1)

    # --- the Khanate business visa (paper sticker) ---
    vx, vy, vw, vh = 26, 70, 438, 138
    d.rectangle([vx, vy, vx + vw, vy + vh], fill=(238, 240, 228),
                outline=VISA_GREEN, width=2)
    d.rectangle([vx + 5, vy + 5, vx + vw - 5, vy + vh - 5],
                outline=VISA_GREEN, width=1)
    draw_centered(d, vx + vw // 2, vy + 12, "TARKHAN KHANATE",
                  font(15, bold=True), fill=VISA_GREEN)
    draw_centered(d, vx + vw // 2, vy + 32, "BUSINESS VISA  ·  No. 0441",
                  font(12, bold=True), fill=VISA_GREEN)
    vf = font(12)
    d.text((vx + 16, vy + 56), "Issued:  02 JUN 2024", font=vf, fill=INK)
    d.text((vx + 16, vy + 74), "Valid:  02 JUN 2024 — 30 SEP 2024",
           font=vf, fill=INK)
    d.text((vx + 240, vy + 56), "Entries:  MULTIPLE", font=vf, fill=INK)
    d.text((vx + 240, vy + 74), "Stay:  90 DAYS", font=vf, fill=INK)
    d.text((vx + 16, vy + 96),
           "CONDITION: TRADE IN WOOL AND AMBER ONLY.",
           font=font(11, bold=True), fill=VISA_GREEN)
    d.text((vx + 16, vy + 112), "EMPLOYMENT PROHIBITED.",
           font=font(11, bold=True), fill=VISA_GREEN)

    # --- border stamps: two columns, four rows ---
    stamps = [
        # (country, kind, place, date, colour, angle)
        ("ZALISSIA", "EXIT", "ZALISSK RAIL TERMINAL", "03 MAR 2024",
         STAMP_BLUE, -5),
        ("BOROVNYA", "ENTRY", "DROVSK", "03 MAR 2024", STAMP_PURPLE, 4),
        ("BOROVNYA", "EXIT", "DROVSK", "21 MAR 2024", STAMP_BLUE, 3),
        ("ZALISSIA", "ENTRY", "ZALISSK", "21 MAR 2024", STAMP_PURPLE, -6),
        ("ZALISSIA", "EXIT", "ZALISSK RAIL TERMINAL", "09 JUN 2024",
         STAMP_BLUE, -3),
        ("TARKHAN KHANATE", "ENTRY", "QARASHAHR", "10 JUN 2024",
         STAMP_PURPLE, 6),
        ("TARKHAN KHANATE", "EXIT", "QARASHAHR", "28 JUN 2024",
         STAMP_BLUE, 5),
        ("ZALISSIA", "ENTRY", "ZALISSK", "29 JUN 2024", STAMP_PURPLE, -4),
    ]
    col_x = (26 + 108, 256 + 108)
    row_y = (258, 360, 462, 564)
    for i, (country, kind, place, date, color, angle) in enumerate(stamps):
        stamp = make_stamp(country, kind, place, date, color)
        paste_stamp(pg, stamp, col_x[i % 2], row_y[i // 2], angle)

    # --- transit fee stamp, paid in cash at the border ---
    fee = make_fee_stamp("TRANSIT FEE 40 ZAL — PAID", "09 JUN 2024 · ZALISSK")
    paste_stamp(pg, fee, 245, 652, -8)
    return pg


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------

def main():
    canvas = Image.new("RGB", (W, H), DESK)
    d = ImageDraw.Draw(canvas, "RGBA")

    # desk speckles (fixed seed -> deterministic)
    for _ in range(1600):
        x = RNG.randrange(W)
        y = RNG.randrange(H)
        v = RNG.randrange(28, 62)
        d.point((x, y), fill=(v, v + 2, v + 5))

    # soft drop shadow under the whole spread
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([28, 172, 1004, 872], fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(shadow, (0, 0), shadow)

    left = build_data_page()
    right = build_visa_page()
    canvas.paste(left, (22, 164))
    canvas.paste(right, (512, 164))

    # centre spine shading between the two pages
    spine = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    spd = ImageDraw.Draw(spine)
    for i in range(10):
        spd.line([(512 - i, 164), (512 - i, 860)],
                 fill=(0, 0, 0, 26 - 2 * i))
        spd.line([(512 + i, 164), (512 + i, 860)],
                 fill=(0, 0, 0, 26 - 2 * i))
    canvas.paste(spine, (0, 0), spine)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    canvas.save(OUT, format="PNG", optimize=True)
    os.chmod(OUT, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
