#!/usr/bin/env python3
"""Generate the original pixel-art barbarian run cycle for the queue scene.

Output: assets/pixel-trynd-run.png  - 6 frames, 40x40 logical px each, in one row (240x40).
The overlay scales it up with image-rendering:pixelated. Original art (not a Riot sprite).
Run:  python3 scripts/make_pixel_trynd.py
"""
from pathlib import Path
from PIL import Image

W = H = 40
C = {
    "K": (16, 18, 24),     # outline
    "S": (226, 170, 124), "s": (178, 120, 84),      # skin
    "H": (34, 24, 24), "h": (74, 52, 46),           # hair
    "T": (78, 110, 146), "t": (52, 76, 104), "u": (112, 146, 180),  # tunic (blue/grey)
    "F": (222, 214, 196), "f": (160, 150, 132),     # fur
    "L": (110, 66, 36), "l": (72, 42, 22),          # leather
    "G": (214, 164, 58),                            # gold
    "P": (54, 60, 74), "p": (36, 40, 52),           # pants
    "B": (70, 48, 34), "b": (46, 30, 22),           # boots
    "W": (232, 240, 248), "w": (150, 170, 190), "v": (98, 116, 136),  # blade
    "R": (220, 24, 32), "r": (140, 12, 20), "O": (255, 92, 60),        # rage red
}

def line(px, x0, y0, x1, y1, col, th=1):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        for ox in range(th):
            for oy in range(th):
                px[(x0 + ox, y0 + oy)] = col
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy

def rect(px, x0, y0, x1, y1, col):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            px[(x, y)] = col

def leg(px, hip, knee, foot, dark):
    th, sh, bt = ("p", "p", "b") if dark else ("P", "P", "B")
    line(px, hip[0], hip[1], knee[0], knee[1], th, 3)
    line(px, knee[0], knee[1], foot[0], foot[1] - 2, sh, 2)
    # boot (fur cuff + sole) pointing right
    rect(px, foot[0] - 1, foot[1] - 3, foot[0] + 1, foot[1] - 3, "f" if dark else "F")
    rect(px, foot[0] - 1, foot[1] - 2, foot[0] + 2, foot[1], bt)

# 6-frame run: contact, down, passing (x2 with legs swapped). bob: + = lower
BOB = [0, 1, -1, 0, 1, -1]
# (knee, foot) relative to hip, for leg A / leg B
LEG_A = [((3, 5), (6, 11)), ((3, 5), (3, 11)), ((1, 5), (0, 11)),
         ((-3, 4), (-7, 8)), ((-2, 5), (-6, 6)), ((2, 3), (-1, 7))]
LEG_B = LEG_A[3:] + LEG_A[:3]
HAIR_WAVE = [0, 1, 2, 1, 0, -1]
BACK_HAND = [(-4, 5), (-3, 6), (-1, 7), (2, 6), (1, 7), (-2, 6)]   # back arm swings opposite to the near leg

def frame(i):
    px = {}
    b = BOB[i]
    hip = (19, 26 + b)
    # ---- back leg (darker) + back arm (behind the body)
    near_leg, far_leg = (LEG_A[i], LEG_B[i])
    k, f = far_leg
    leg(px, hip, (hip[0] + k[0], hip[1] + k[1]), (hip[0] + f[0], min(38, hip[1] + f[1])), True)
    sh_back = (17, 18 + b)
    bh = BACK_HAND[i]
    line(px, sh_back[0], sh_back[1], sh_back[0] + bh[0], sh_back[1] + bh[1], "s", 2)
    # ---- hair flowing behind (long, dark)
    w = HAIR_WAVE[i]
    for row in range(10, 23):
        t = row - 10
        x_end = 15 - t // 2 - (w if t > 5 else 0)
        x_start = 18 if row < 15 else 16
        for x in range(max(5, x_end), x_start + 1):
            px[(x, row + b)] = "H" if (x + row) % 5 else "h"
    # red rage sash trailing from the belt
    for j, (dx, dy) in enumerate([(0, 0), (-1, 0), (-2, 1), (-3, 1), (-4, 2), (-5, 2 + (w > 0)), (-6, 3 + (w > 0))]):
        px[(15 + dx, 24 + dy + b)] = "R" if j < 5 else "r"
        if j < 4:
            px[(15 + dx, 25 + dy + b)] = "r"
    # ---- torso: tunic
    rect(px, 15, 18 + b, 22, 26 + b, "T")
    rect(px, 15, 18 + b, 16, 26 + b, "t")
    rect(px, 21, 19 + b, 22, 23 + b, "u")
    # tunic skirt flaps
    rect(px, 15, 27 + b, 22, 28 + b, "t")
    px[(22 + (i % 2), 29 + b)] = "t"; px[(16 - (i % 2), 29 + b)] = "t"
    # belt + buckle + red sash knot
    rect(px, 15, 24 + b, 22, 25 + b, "L")
    rect(px, 15, 25 + b, 22, 25 + b, "l")
    rect(px, 19, 24 + b, 20, 25 + b, "G")
    px[(15, 24 + b)] = "R"; px[(16, 24 + b)] = "R"
    # ---- near leg (in front)
    k, f = near_leg
    leg(px, (hip[0] + 1, hip[1]), (hip[0] + 1 + k[0], hip[1] + k[1]), (hip[0] + 1 + f[0], min(38, hip[1] + f[1])), False)
    # ---- fur mantle over the shoulders
    for x in range(13, 24):
        top = 16 + b + (1 if x in (13, 23) else 0)
        for y in range(top, 20 + b):
            px[(x, y)] = "F" if (x * 3 + y) % 4 else "f"
    rect(px, 13, 20 + b, 15, 20 + b, "f"); px[(21, 20 + b)] = "f"; px[(23, 20 + b)] = "f"
    # ---- head (facing right)
    hx, hy = 17, 8 + b
    rect(px, hx + 1, hy + 2, hx + 6, hy + 8, "S")          # face block
    rect(px, hx + 1, hy + 7, hx + 5, hy + 8, "s")          # jaw shade / stubble
    px[(hx + 3, hy + 8)] = "h"; px[(hx + 4, hy + 8)] = "s"
    px[(hx + 7, hy + 5)] = "S"                              # nose
    px[(hx + 5, hy + 4)] = "K"                              # eye
    px[(hx + 4, hy + 3)] = "H"; px[(hx + 5, hy + 3)] = "H"  # angry brow
    px[(hx + 6, hy + 3)] = "H"
    px[(hx + 5, hy + 7)] = "r"; px[(hx + 6, hy + 7)] = "r"  # war-cry mouth
    rect(px, hx - 1, hy, hx + 6, hy + 1, "H")              # hair cap
    rect(px, hx - 1, hy + 2, hx + 2, hy + 8, "H")          # hair at the back of the head
    px[(hx + 3, hy + 2)] = "H"; px[(hx + 7, hy + 1)] = "H"
    px[(hx + 1, hy - 1)] = "H"; px[(hx + 3, hy - 1)] = "H"; px[(hx + 4, hy - 1)] = "h"
    px[(hx + 2, hy)] = "h"; px[(hx + 4, hy)] = "h"
    rect(px, hx - 1, hy + 2, hx + 1, hy + 2, "R")          # red headband accent
    px[(hx - 2, hy + 3)] = "R"; px[(hx - 3, hy + 4 + (i % 2))] = "r"
    # ---- sword arm + big sword held up
    sway = 0
    hand = (26, 20 + b)
    line(px, 21, 19 + b, hand[0], hand[1], "S", 2)
    px[(23, 21 + b)] = "s"
    # blade: from crossguard up, slight backward lean
    top = (27 - sway, 0)
    base = (27, hand[1] - 3)
    bx = 26
    for yy in range(1, hand[1] - 2):
        px[(bx, yy)] = "w"; px[(bx + 1, yy)] = "W"; px[(bx + 2, yy)] = "W"; px[(bx + 3, yy)] = "v"
    for yy in range(5, hand[1] - 4):
        px[(bx + 1, yy)] = "v" if yy % 2 else "W"                      # fuller
    rect(px, bx + 1, 0, bx + 2, 0, "W")                                 # tip
    for yy in range(hand[1] - 5, 3, -4):
        px[(bx + 3, yy)] = "R"                                          # rage-red edge runes
    # crossguard + grip + pommel
    rect(px, 23, hand[1] - 2, 32, hand[1] - 2, "G")
    rect(px, 24, hand[1] - 1, 31, hand[1] - 1, "l")
    px[(22, hand[1] - 2)] = "R"; px[(33, hand[1] - 2)] = "R"
    rect(px, 27, hand[1], 28, hand[1] + 3, "L")             # grip
    rect(px, 27, hand[1] + 4, 28, hand[1] + 4, "G")         # pommel
    rect(px, 25, hand[1], 29, hand[1] + 1, "S")             # fist wrapped round the grip
    px[(25, hand[1] + 1)] = "s"; px[(29, hand[1] + 1)] = "s"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    filled = {p for p in px if 0 <= p[0] < W and 0 <= p[1] < H}
    # auto outline around the silhouette
    for (x, y) in list(filled):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q not in filled and 0 <= q[0] < W and 0 <= q[1] < H:
                img.putpixel(q, C["K"] + (255,))
    for p in filled:
        img.putpixel(p, C[px[p]] + (255,))
    return img

def main():
    out = Path(__file__).resolve().parent.parent / "assets" / "pixel-trynd-run.png"
    sheet = Image.new("RGBA", (W * 6, H), (0, 0, 0, 0))
    for i in range(6):
        sheet.paste(frame(i), (i * W, 0))
    sheet.save(out)
    print("wrote", out, sheet.size)

if __name__ == "__main__":
    main()
