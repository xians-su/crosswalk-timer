#!/usr/bin/env python3
"""Home-screen icon: the page's progress bar in the company logo's colours (cyan = may cross, gray = wait),
with the logo's slanted yellow-to-cyan "i" as the pointer and a four-petal yellow sprout on top. White ground."""
from PIL import Image, ImageDraw
import math, sys
S = 4; N = 1024 * S                                             # draw at 4x and scale down for clean edges
WHITE, L_GRAY, L_CYAN, L_YEL = (255, 255, 255), (89, 86, 86), (0, 175, 213), (230, 228, 0)   # sampled from the SpringTrees logo

def capline(d, p, q, w, fill):
    d.line([(p[0] * S, p[1] * S), (q[0] * S, q[1] * S)], fill=fill, width=round(w * S))
    for (x, y) in (p, q): d.ellipse([(x - w / 2) * S, (y - w / 2) * S, (x + w / 2) * S, (y + w / 2) * S], fill=fill)

im = Image.new('RGB', (N, N), WHITE)
# bar: cyan up to the split, gray after, fully rounded
x0, x1, yc, hgt, split = 92, 932, 640, 176, 432
lay = Image.new('RGB', (N, N), L_GRAY); ImageDraw.Draw(lay).rectangle([0, 0, split * S, N], fill=L_CYAN)
m = Image.new('L', (N, N), 0); ImageDraw.Draw(m).rounded_rectangle([x0 * S, (yc - hgt / 2) * S, x1 * S, (yc + hgt / 2) * S], hgt / 2 * S, fill=255)
im.paste(lay, (0, 0), m)
# pointer: the logo's slanted i, yellow at the top fading to cyan, with a white outline so it reads over the bar
bottom, top, w, ring = (296, 766), (352, 450), 64, 14
d = ImageDraw.Draw(im); capline(d, bottom, top, w + 2 * ring, WHITE)
m = Image.new('L', (N, N), 0); capline(ImageDraw.Draw(m), bottom, top, w, 255)
g = Image.new('RGB', (N, N)); gd = ImageDraw.Draw(g); y0, y1 = (top[1] - w / 2) * S, (bottom[1] + w / 2) * S
for y in range(int(y0), int(y1) + 1):
    f = min(1, max(0, (y - y0) / (y1 - y0))); f = f * f * (3 - 2 * f)
    gd.line([(0, y), (N, y)], fill=tuple(round(L_YEL[i] + (L_CYAN[i] - L_YEL[i]) * f) for i in range(3)))
im.paste(g, (0, 0), m)
# sprout: four separate round petals on the diagonals
c, r = (372, 328), 62; d = ImageDraw.Draw(im)
for k in range(4):
    a = math.radians(45 + 90 * k); x = c[0] + r * 0.80 * math.cos(a); y = c[1] + r * 0.80 * math.sin(a); q = r * 0.72
    d.ellipse([(x - q) * S, (y - q) * S, (x + q) * S, (y + q) * S], fill=L_YEL)
im = im.resize((1024, 1024), Image.LANCZOS)
im.resize((180, 180), Image.LANCZOS).save('icon.png'); im.resize((512, 512), Image.LANCZOS).save('icon-512.png'); im.resize((48, 48), Image.LANCZOS).save('favicon.png')
if len(sys.argv) > 1:
    pv = Image.new('RGB', (360 + 20 + 120 + 20 + 60, 360), (136, 136, 136)); pv.paste(im.resize((360, 360), Image.LANCZOS), (0, 0)); pv.paste(im.resize((120, 120), Image.LANCZOS), (380, 0)); pv.paste(im.resize((60, 60), Image.LANCZOS), (520, 0)); pv.save(sys.argv[1])
