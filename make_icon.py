#!/usr/bin/env python3
"""Home-screen icon: four striding signal figures on a zebra crossing, in the company palette."""
from PIL import Image, ImageDraw
N = 1024
GRAY, GRAY2, CYAN, GREEN, YELLOW, WHITE = (43, 48, 56), (27, 31, 37), (8, 185, 224), (159, 207, 46), (230, 228, 0), (255, 255, 255)
im = Image.new('RGB', (N, N)); d = ImageDraw.Draw(im)
for y in range(N):
    f = y / (N - 1); d.line([(0, y), (N, y)], fill=tuple(round(GRAY[i] + (GRAY2[i] - GRAY[i]) * f) for i in range(3)))
# zebra crossing: slanted white bars along the bottom
top, bot, w, gap, skew = 720, 905, 104, 62, 34
x = -20
while x < N:
    d.polygon([(x + skew, top), (x + skew + w, top), (x + w, bot), (x, bot)], fill=WHITE); x += w + gap

def limb(p, q, wd, col):
    d.line([p, q], fill=col, width=wd)
    for (px, py) in (p, q): d.ellipse((px - wd / 2, py - wd / 2, px + wd / 2, py + wd / 2), fill=col)

def walker(cx, base, h, col, sprout=False):
    wd = round(h * 0.115); neck = (cx + h * 0.03, base - h * 0.78); hip = (cx - h * 0.02, base - h * 0.42)
    limb(neck, hip, round(wd * 1.25), col)                                     # torso
    limb(hip, (cx + h * 0.20, base - wd / 2), wd, col)                          # front leg
    limb(hip, (cx - h * 0.21, base - wd / 2), wd, col)                          # back leg
    sh = (cx + h * 0.02, base - h * 0.72)
    limb(sh, (cx - h * 0.17, base - h * 0.47), round(wd * 0.85), col)           # back arm
    limb(sh, (cx + h * 0.19, base - h * 0.50), round(wd * 0.85), col)           # front arm
    r = h * 0.095; hc = (cx + h * 0.05, base - h * 0.905)
    d.ellipse((hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r), fill=col)
    if sprout:                                                                  # the sprout from the logo's "i"
        s = h * 0.075; c = (hc[0] + h * 0.01, hc[1] - r - s * 1.25)
        limb((c[0] - s, c[1]), (c[0] + s, c[1]), round(s * 0.62), YELLOW); limb((c[0], c[1] - s), (c[0], c[1] + s), round(s * 0.62), YELLOW)

for i, col in enumerate((CYAN, GREEN, CYAN, GREEN)):
    walker(170 + i * 228, top + 6, 455, col, sprout=(i == 3))
im.resize((180, 180), Image.LANCZOS).save('icon.png'); im.resize((512, 512), Image.LANCZOS).save('icon-512.png'); im.resize((48, 48), Image.LANCZOS).save('favicon.png')
import sys
if len(sys.argv) > 1:
    pv = Image.new('RGB', (360 + 20 + 120 + 20 + 60, 360), (136, 136, 136)); pv.paste(im.resize((360, 360), Image.LANCZOS), (0, 0)); pv.paste(im.resize((120, 120), Image.LANCZOS), (380, 0)); pv.paste(im.resize((60, 60), Image.LANCZOS), (520, 0)); pv.save(sys.argv[1])
