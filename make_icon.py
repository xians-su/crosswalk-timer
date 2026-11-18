#!/usr/bin/env python3
"""Home-screen icon: four striding signal figures on a zebra crossing, in the company palette."""
from PIL import Image, ImageDraw
N = 1024
GRAY, GRAY2, CYAN, GREEN, YELLOW, WHITE = (43, 48, 56), (27, 31, 37), (8, 185, 224), (159, 207, 46), (230, 228, 0), (255, 255, 255)
im = Image.new('RGB', (N, N)); d = ImageDraw.Draw(im)
for y in range(N):
    f = y / (N - 1); d.line([(0, y), (N, y)], fill=tuple(round(GRAY[i] + (GRAY2[i] - GRAY[i]) * f) for i in range(3)))
# zebra crossing: slanted white bars along the bottom
top, bot, w, gap, skew = 716, 900, 100, 58, 40
x = -20
while x < N:
    d.polygon([(x + skew, top), (x + skew + w, top), (x + w, bot), (x, bot)], fill=WHITE); x += w + gap

def limb(p, q, wd, col):
    d.line([p, q], fill=col, width=wd)
    for (px, py) in (p, q): d.ellipse((px - wd / 2, py - wd / 2, px + wd / 2, py + wd / 2), fill=col)

def walker(cx, base, h, col, sprout=False):
    """Mid-stride figure walking right: leaning torso, bent front knee, trailing back leg, opposite arm swing."""
    wd = round(h * 0.125)
    neck = (cx + h * 0.045, base - h * 0.77); hip = (cx - h * 0.015, base - h * 0.43)
    limb(neck, hip, round(wd * 1.3), col)
    kf = (cx + h * 0.13, base - h * 0.23); limb(hip, kf, wd, col); limb(kf, (cx + h * 0.235, base - wd / 2), wd, col)      # front leg
    kb = (cx - h * 0.10, base - h * 0.22); limb(hip, kb, wd, col); limb(kb, (cx - h * 0.25, base - wd / 2 - h * 0.035), wd, col)  # back leg, heel up
    sh = (cx + h * 0.035, base - h * 0.71); aw = round(wd * 0.82)
    eb = (cx - h * 0.095, base - h * 0.585); limb(sh, eb, aw, col); limb(eb, (cx - h * 0.19, base - h * 0.50), aw, col)     # back arm
    ef = (cx + h * 0.13, base - h * 0.60); limb(sh, ef, aw, col); limb(ef, (cx + h * 0.225, base - h * 0.555), aw, col)     # front arm
    r = h * 0.1; hc = (cx + h * 0.075, base - h * 0.905)
    d.ellipse((hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r), fill=col)
    if sprout:                                                                  # the sprout from the logo's "i"
        s = h * 0.085; c = (hc[0], hc[1] - r - s * 1.3)
        limb((c[0] - s, c[1]), (c[0] + s, c[1]), round(s * 0.66), YELLOW); limb((c[0], c[1] - s), (c[0], c[1] + s), round(s * 0.66), YELLOW)

for i, col in enumerate((CYAN, GREEN, CYAN, GREEN)):
    walker(142 + i * 238, top + 8, 430, col, sprout=(i == 3))
im.resize((180, 180), Image.LANCZOS).save('icon.png'); im.resize((512, 512), Image.LANCZOS).save('icon-512.png'); im.resize((48, 48), Image.LANCZOS).save('favicon.png')
import sys
if len(sys.argv) > 1:
    pv = Image.new('RGB', (360 + 20 + 120 + 20 + 60, 360), (136, 136, 136)); pv.paste(im.resize((360, 360), Image.LANCZOS), (0, 0)); pv.paste(im.resize((120, 120), Image.LANCZOS), (380, 0)); pv.paste(im.resize((60, 60), Image.LANCZOS), (520, 0)); pv.save(sys.argv[1])
