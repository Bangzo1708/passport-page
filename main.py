#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Writes one invented passport spread (1024x1024 PNG) to /output/entry.png
using ONLY the Python standard library.  No Pillow, no numpy, no network.

Design: an open passport of the invented Republic of Zalissia on a dark
slate desk.  Left page: data page with coat of arms, portrait, personal
fields and a machine-readable zone.  Right page: a Tarkhan Khanate
business-visa sticker, eight consistent entry/exit border stamps and a
red transit-fee stamp.

Rendering is span-based (slice assignment on a bytearray canvas) so the
whole image renders in a few seconds on one CPU.  Text uses a hand-made
5x7 bitmap font defined below.  The PNG encoder is struct + zlib.
Everything is deterministic (fixed seed, ordered lists only).
"""

import math
import os
import random
import struct
import zlib

W, H = 1024, 1024
OUT = os.environ.get("ENTRY_OUT", "/output/entry.png")
RNG = random.Random(20261121)

# ---------------------------------------------------------------- palette
DESK = (38, 41, 46)
CREAM = (243, 238, 222)
CREAM_DARK = (232, 224, 200)
PAGE_LINE = (198, 188, 162)
INK = (32, 30, 26)
INK_SOFT = (84, 78, 66)
GOLD = (198, 164, 74)
GREEN = (34, 110, 66)
GREEN_DARK = (24, 78, 48)
BLUE = (38, 74, 143)
PURPLE = (104, 63, 150)
RED = (178, 44, 38)
SKIN = (228, 192, 162)
HAIR = (52, 38, 30)
JACKET = (46, 92, 64)
PORTRAIT_BG = (168, 178, 194)
KEY = (255, 0, 255)  # transparency key for stamp sprites


# ------------------------------------------------------------------ canvas
class Canvas:
    """RGB bytearray canvas with span-based drawing primitives."""

    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(color) * (w * h))

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        stride = self.w * 3
        for yy in range(y0, y1):
            i = yy * stride + x0 * 3
            self.buf[i:i + len(row)] = row

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def get_px(self, x, y):
        i = (y * self.w + x) * 3
        return (self.buf[i], self.buf[i + 1], self.buf[i + 2])

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_px(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect_outline(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        """Scanline-filled ellipse."""
        for yy in range(cy - ry, cy + ry + 1):
            dy = (yy - cy) / ry
            if abs(dy) > 1:
                continue
            hw = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
            self.fill_rect(cx - hw, yy, 2 * hw + 1, 1, color)

    def fill_poly(self, pts, color):
        """Scanline-filled polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(pts)
        for yy in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y_a = pts[i]
                x1, y_b = pts[(i + 1) % n]
                if y_a == y_b:
                    continue
                if (y_a <= yy < y_b) or (y_b <= yy < y_a):
                    t = (yy - y_a) / (y_b - y_a)
                    xs.append(x0 + t * (x1 - x0))
            if len(xs) < 2:
                continue
            xs.sort()
            xa, xb = int(round(xs[0])), int(round(xs[-1]))
            self.fill_rect(xa, yy, xb - xa + 1, 1, color)


# -------------------------------------------------------------------- font
# Hand-made 5x7 bitmap font.  Each glyph is 7 rows of 5 '0'/'1' chars.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "10010"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
}


def text_width(s, scale=2, advance=None):
    adv = advance if advance is not None else 6 * scale
    return max(0, len(s) * adv - (adv - 5 * scale))


def draw_text(cv, x, y, s, color, scale=2, advance=None):
    """Draw text on canvas cv; returns width drawn."""
    adv = advance if advance is not None else 6 * scale
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += adv
            continue
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == "1":
                    cv.fill_rect(cx + col_i * scale, y + row_i * scale,
                                 scale, scale, color)
        cx += adv
    return cx - x


def draw_text_center(cv, cx, y, s, color, scale=2, advance=None):
    w = text_width(s, scale, advance)
    return draw_text(cv, cx - w // 2, y, s, color, scale, advance)


# --------------------------------------------------------------------- MRZ
def mrz_check(s):
    """ICAO 9303 check digit: values 0-9, A-Z=10-35, '<'=0; weights 7,3,1."""
    total = 0
    for i, ch in enumerate(s):
        if ch == "<":
            v = 0
        elif "0" <= ch <= "9":
            v = ord(ch) - 48
        else:
            v = ord(ch) - 55
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = ("P<ZAL" + "KOVAL<<MARA<ILLYNA").ljust(44, "<")
    doc = "ZA8472913"
    dob = "880314"
    exp = "340212"
    filler = "<" * 14
    body = (doc + mrz_check(doc) + "ZAL" + dob + mrz_check(dob) + "F"
            + exp + mrz_check(exp) + filler + mrz_check(filler))
    line2 = body + mrz_check(body)
    assert len(line1) == 44 and len(line2) == 44
    return line1, line2


# -------------------------------------------------------------- primitives
def star_points(cx, cy, r_out, r_in, rot=-90.0):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 36.0)
        pts.append((cx + int(round(r * math.cos(a))),
                    cy + int(round(r * math.sin(a)))))
    return pts


def blit_rotated(dst, src, cx, cy, angle_deg):
    """Blit sprite canvas src onto dst, rotated about (cx, cy).

    Inverse mapping, nearest neighbour, only inside the rotated bbox;
    KEY-coloured pixels are transparent.
    """
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = src.w / 2.0, src.h / 2.0
    ex = int(abs(hw * ca) + abs(hh * sa)) + 1
    ey = int(abs(hw * sa) + abs(hh * ca)) + 1
    for dy in range(-ey, ey + 1):
        for dx in range(-ex, ex + 1):
            # inverse rotation: source offset from sprite centre
            sx = dx * ca + dy * sa + hw
            sy = -dx * sa + dy * ca + hh
            ix, iy = int(sx), int(sy)
            if 0 <= ix < src.w and 0 <= iy < src.h:
                px = src.get_px(ix, iy)
                if px != KEY:
                    dst.set_px(cx + dx, cy + dy, px)


def wavy_line(cv, x0, x1, y_base, amp, period, color):
    prev = None
    x = x0
    while x <= x1:
        y = y_base + int(round(amp * math.sin(2 * math.pi * x / period)))
        if prev is not None:
            cv.line(prev[0], prev[1], x, y, color)
        prev = (x, y)
        x += 6


# ------------------------------------------------------------ coat of arms
def draw_arms(cv, cx, y):
    """Green shield, gold frame, white pine, one gold star."""
    # outer (gold) shield, then inner (green) shield
    outer = [(cx - 40, y), (cx + 40, y), (cx + 40, y + 54),
             (cx, y + 92), (cx - 40, y + 54)]
    inner = [(cx - 34, y + 5), (cx + 34, y + 5), (cx + 34, y + 52),
             (cx, y + 84), (cx - 34, y + 52)]
    cv.fill_poly(outer, GOLD)
    cv.fill_poly(inner, GREEN)
    # gold star at the top of the shield
    cv.fill_poly(star_points(cx, y + 18, 9, 4), GOLD)
    # white pine: three stacked triangles + trunk
    pine_cx, pine_base = cx, y + 76
    cv.fill_poly([(pine_cx - 13, pine_base - 26), (pine_cx + 13, pine_base - 26),
                  (pine_cx, pine_base - 44)], (244, 246, 240))
    cv.fill_poly([(pine_cx - 17, pine_base - 12), (pine_cx + 17, pine_base - 12),
                  (pine_cx, pine_base - 34)], (244, 246, 240))
    cv.fill_poly([(pine_cx - 20, pine_base), (pine_cx + 20, pine_base),
                  (pine_cx, pine_base - 24)], (244, 246, 240))
    cv.fill_rect(pine_cx - 3, pine_base, 6, 8, (244, 246, 240))


# ---------------------------------------------------------------- portrait
def draw_portrait(cv, x, y, w, h):
    """Stylised portrait: dark-braided woman, green jacket, pale blue-grey."""
    cv.fill_rect(x, y, w, h, PORTRAIT_BG)
    cx = x + w // 2
    # shoulders / jacket
    cv.fill_poly([(x + 8, y + h), (x + w - 8, y + h),
                  (x + w - 26, y + h - 52), (x + 26, y + h - 52)], JACKET)
    cv.fill_poly([(x + 26, y + h - 52), (x + w - 26, y + h - 52),
                  (x + w - 34, y + h - 30), (x + 34, y + h - 30)], (36, 74, 52))
    # neck
    cv.fill_rect(cx - 11, y + 96, 22, 26, SKIN)
    # hair mass behind the head
    cv.fill_ellipse(cx, y + 62, 40, 48, HAIR)
    # braids falling over both shoulders
    cv.fill_ellipse(cx - 36, y + 118, 11, 34, HAIR)
    cv.fill_ellipse(cx + 36, y + 118, 11, 34, HAIR)
    # face
    cv.fill_ellipse(cx, y + 64, 31, 40, SKIN)
    # hairline fringe
    cv.fill_ellipse(cx, y + 34, 31, 16, HAIR)
    cv.fill_rect(cx - 31, y + 26, 62, 12, HAIR)
    # eyes, brows, nose, mouth
    cv.fill_ellipse(cx - 13, y + 62, 4, 3, (30, 24, 20))
    cv.fill_ellipse(cx + 13, y + 62, 4, 3, (30, 24, 20))
    cv.fill_rect(cx - 18, y + 54, 11, 2, HAIR)
    cv.fill_rect(cx + 7, y + 54, 11, 2, HAIR)
    cv.vline(cx, y + 66, 12, (196, 150, 122))
    cv.fill_rect(cx - 8, y + 88, 16, 3, (168, 96, 84))
    # jacket collar + shirt V
    cv.fill_poly([(cx - 16, y + h - 52), (cx + 16, y + h - 52),
                  (cx, y + h - 26)], (236, 232, 220))
    cv.fill_rect(cx - 2, y + h - 52, 4, 12, (30, 30, 28))
    # thin frame
    cv.rect_outline(x, y, w, h, (120, 122, 128), 2)


# --------------------------------------------------------------- data page
def draw_data_page(cv):
    px, py, pw, ph = 22, 164, 490, 696
    # page + inner border + faint guilloche
    cv.fill_rect(px, py, pw, ph, CREAM)
    cv.rect_outline(px + 7, py + 7, pw - 14, ph - 14, PAGE_LINE, 1)
    wavy_line(cv, px + 14, px + pw - 14, py + 150, 4, 90, CREAM_DARK)
    wavy_line(cv, px + 14, px + pw - 14, py + 560, 4, 110, CREAM_DARK)

    # coat of arms + titles
    draw_arms(cv, px + pw // 2, py + 26)
    draw_text_center(cv, px + pw // 2, py + 132, "REPUBLIC OF ZALISSIA",
                     GREEN_DARK, 3)
    draw_text_center(cv, px + pw // 2, py + 160, "PASSPORT", INK, 4)
    cv.fill_rect(px + 90, py + 190, pw - 180, 2, GOLD)

    # portrait (left) and document codes (right)
    draw_portrait(cv, px + 26, py + 206, 140, 176)
    rx = px + 190
    draw_text(cv, rx, py + 210, "Type", INK_SOFT, 2)
    draw_text(cv, rx, py + 228, "P", INK, 3)
    draw_text(cv, rx + 90, py + 210, "Code", INK_SOFT, 2)
    draw_text(cv, rx + 90, py + 228, "ZAL", INK, 3)
    draw_text(cv, rx, py + 268, "Passport No.", INK_SOFT, 2)
    draw_text(cv, rx, py + 286, "ZA8472913", INK, 3)
    draw_text(cv, rx, py + 322, "Holder of this passport is", INK_SOFT, 1)
    draw_text(cv, rx, py + 334, "a citizen of Zalissia.", INK_SOFT, 1)
    draw_text(cv, rx, py + 352, "Issued in Zalissk.", INK_SOFT, 1)

    # personal fields: (label, value, x, y) -- two columns
    fields = [
        ("Surname", "KOVAL", px + 26, py + 406),
        ("Given names", "MARA ILLYNA", px + 250, py + 406),
        ("Nationality", "ZALISSIAN", px + 26, py + 446),
        ("Sex", "F", px + 250, py + 446),
        ("Date of birth", "14 MAR 1988", px + 26, py + 486),
        ("Place of birth", "ZALISSK", px + 250, py + 486),
        ("Date of issue", "12 FEB 2024", px + 26, py + 526),
        ("Date of expiry", "12 FEB 2034", px + 250, py + 526),
    ]
    for label, value, fx, fy in fields:
        draw_text(cv, fx, fy, label, INK_SOFT, 2)
        draw_text(cv, fx, fy + 18, value, INK, 2)
    draw_text(cv, px + 26, py + 566, "Authority", INK_SOFT, 2)
    draw_text(cv, px + 26, py + 584,
              "MINISTRY OF THE INTERIOR - ZALISSK", INK, 2)

    # signature
    draw_text(cv, px + 26, py + 604, "M. Koval", INK, 3)
    cv.hline(px + 26, py + 626, 150, INK_SOFT)

    # machine-readable zone
    mz_y = py + 630
    cv.fill_rect(px + 7, mz_y, pw - 14, 59, (236, 231, 214))
    line1, line2 = mrz_lines()
    draw_text(cv, px + 24, mz_y + 8, line1, INK, 2, advance=10)
    draw_text(cv, px + 24, mz_y + 32, line2, INK, 2, advance=10)


# --------------------------------------------------------------- visa page
def make_stamp(country, kind, place, date, color):
    """Render one border stamp into a small sprite canvas (KEY = clear)."""
    sp = Canvas(210, 78, KEY)
    sp.rect_outline(3, 3, 204, 72, color, 2)
    sp.rect_outline(8, 8, 194, 64, color, 1)
    draw_text_center(sp, 105, 8, country, color, 2)
    draw_text_center(sp, 105, 24, kind, color, 3)
    pscale = 2 if len(place) <= 16 else 1
    draw_text_center(sp, 105, 47, place, color, pscale)
    draw_text_center(sp, 105, 62, date, color, 1)
    return sp


def draw_visa_page(cv):
    px, py, pw, ph = 512, 164, 490, 696
    cv.fill_rect(px, py, pw, ph, CREAM)
    cv.rect_outline(px + 7, py + 7, pw - 14, ph - 14, PAGE_LINE, 1)
    wavy_line(cv, px + 14, px + pw - 14, py + 470, 4, 100, CREAM_DARK)

    draw_text(cv, px + 26, py + 22, "VISAS", INK, 4)
    draw_text(cv, px + pw - 52, py + 22, "12", INK_SOFT, 3)
    cv.fill_rect(px + 26, py + 52, pw - 52, 2, INK_SOFT)

    # --- visa sticker
    sx, sy, sw, sh = px + 26, py + 66, pw - 52, 204
    cv.fill_rect(sx, sy, sw, sh, (214, 230, 222))
    cv.rect_outline(sx, sy, sw, sh, GREEN_DARK, 2)
    cv.rect_outline(sx + 5, sy + 5, sw - 10, sh - 10, GREEN_DARK, 1)
    draw_text_center(cv, sx + sw // 2, sy + 10, "TARKHAN KHANATE",
                     GREEN_DARK, 3)
    draw_text_center(cv, sx + sw // 2, sy + 34, "BUSINESS VISA",
                     GREEN_DARK, 2)
    draw_text_center(cv, sx + sw // 2, sy + 52, "No. 0441", INK, 2)
    vx = sx + 16
    rows = [
        ("Issued:", "02 JUN 2024"),
        ("Valid:", "02 JUN 2024 - 30 SEP 2024"),
        ("Entries:", "MULTIPLE"),
        ("Stay:", "90 DAYS"),
    ]
    ry = sy + 74
    for label, value in rows:
        draw_text(cv, vx, ry, label, INK_SOFT, 2)
        draw_text(cv, vx + text_width(label, 2) + 10, ry, value, INK, 2)
        ry += 16
    cv.hline(vx, ry + 2, sw - 32, INK_SOFT)
    draw_text(cv, vx, ry + 8, "CONDITION: TRADE IN WOOL", INK, 2)
    draw_text(cv, vx, ry + 24, "AND AMBER ONLY.", INK, 2)
    draw_text(cv, vx, ry + 40, "EMPLOYMENT PROHIBITED.", RED, 2)

    # --- border stamps, 2 columns x 4 rows
    stamps = [
        ("ZALISSIA", "EXIT", "ZALISSK RAIL TERMINAL", "03 MAR 2024", BLUE, -5),
        ("BOROVNYA", "ENTRY", "DROVSK", "03 MAR 2024", PURPLE, 4),
        ("BOROVNYA", "EXIT", "DROVSK", "21 MAR 2024", BLUE, 3),
        ("ZALISSIA", "ENTRY", "ZALISSK", "21 MAR 2024", PURPLE, -6),
        ("ZALISSIA", "EXIT", "ZALISSK RAIL TERMINAL", "09 JUN 2024", BLUE, -3),
        ("TARKHAN KHANATE", "ENTRY", "QARASHAHR", "10 JUN 2024", PURPLE, 6),
        ("TARKHAN KHANATE", "EXIT", "QARASHAHR", "28 JUN 2024", BLUE, 5),
        ("ZALISSIA", "ENTRY", "ZALISSK", "29 JUN 2024", PURPLE, -4),
    ]
    gy = py + 284
    for i, (country, kind, place, date, color, angle) in enumerate(stamps):
        col = i % 2
        row = i // 2
        cx = px + 26 + 105 + col * 224
        cy = gy + 39 + row * 80
        sprite = make_stamp(country, kind, place, date, color)
        blit_rotated(cv, sprite, cx, cy, angle)

    # --- red transit-fee stamp
    fee = Canvas(340, 48, KEY)
    fee.rect_outline(2, 2, 336, 44, RED, 2)
    fee.rect_outline(6, 6, 328, 36, RED, 1)
    draw_text_center(fee, 170, 11, "TRANSIT FEE 40 ZAL - PAID", RED, 2)
    draw_text_center(fee, 170, 29, "09 JUN 2024 - ZALISSK", RED, 2)
    blit_rotated(cv, fee, px + pw // 2, py + 646, -8)


# -------------------------------------------------------------------- build
def build():
    cv = Canvas(W, H, DESK)
    # desk speckles (deterministic)
    for _ in range(2600):
        x = RNG.randrange(W)
        y = RNG.randrange(H)
        c = (44, 47, 52) if RNG.random() < 0.5 else (32, 35, 40)
        cv.set_px(x, y, c)
    # fake soft shadow: stepped offset rects under the spread
    for off, color in ((12, (26, 28, 32)), (8, (30, 32, 36)), (4, (34, 36, 41))):
        cv.fill_rect(22 + off, 164 + off, 980, 696, color)
    draw_data_page(cv)
    draw_visa_page(cv)
    # spine: dark centre line + soft shading strips on both pages
    cv.fill_rect(508, 164, 8, 696, (58, 50, 40))
    cv.fill_rect(504, 164, 4, 696, (214, 204, 182))
    cv.fill_rect(516, 164, 4, 696, (214, 204, 182))
    return cv


# -------------------------------------------------------------- png writer
def png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(cv, path):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += cv.buf[y * stride:(y + 1) * stride]
    png = (b"\x89PNG\r\n\x1a\n"
           + png_chunk(b"IHDR", ihdr)
           + png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + png_chunk(b"IEND", b""))
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)
    return len(png)


def main():
    cv = build()
    n = write_png(cv, OUT)
    print("wrote %s (%d bytes, %dx%d)" % (OUT, n, W, H))


if __name__ == "__main__":
    main()
