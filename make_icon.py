#!/usr/bin/env python3
"""Home-screen icon: four pictogram figures in step on a zebra crossing. Geometry is deliberately regular —
one stroke width, straight limbs, equal spacing, stripes centred under the group — and the four company colours do the varying."""
from PIL import Image, ImageDraw
import sys
S = 4; N = 1024 * S                     # draw at 4x and scale down for clean edges
GRAY, GRAY2 = (46, 51, 60), (26, 29, 35)
CYAN, WHITE, GREEN, YELLOW = (8, 185, 224), (255, 255, 255), (159, 207, 46), (240, 226, 40)
im = Image.new('RGB', (N, N)); d = ImageDraw.Draw(im)
for y in range(N):
    f = y / (N - 1); d.line([(0, y), (N, y)], fill=tuple(round(GRAY[i] + (GRAY2[i] - GRAY[i]) * f) for i in range(3)))

def cap(p, q, w, col):
    d.line([p, q], fill=col, width=round(w))
    for (x, y) in (p, q): d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)

def figure(cx, base, h, col):
    """Pictogram walker: head, straight torso, legs as one inverted V, arms as a smaller one."""
    w = h * 0.118
    hip = (cx, base - h * 0.44); sh = (cx + h * 0.022, base - h * 0.735)
    cap(hip, (cx - h * 0.148, base - w / 2), w, col); cap(hip, (cx + h * 0.148, base - w / 2), w, col)        # legs
    cap(sh, hip, w * 1.28, col)                                                                              # torso
    cap(sh, (cx - h * 0.125, base - h * 0.49), w * 0.8, col); cap(sh, (cx + h * 0.14, base - h * 0.51), w * 0.8, col)   # arms
    r = h * 0.098; hc = (cx + h * 0.04, base - h * 0.90); d.ellipse((hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r), fill=col)

top = 742 * S; step = 216 * S; h = 500 * S
for i, col in enumerate((CYAN, WHITE, GREEN, YELLOW)):
    figure(N / 2 + (i - 1.5) * step, top + 10 * S, h, col)
# zebra: seven equal bars, same slant, centred on the canvas, running off the bottom edge
bw, gap, skew, bot = 92 * S, 58 * S, 34 * S, 932 * S
for k in range(-4, 5):
    x = N / 2 + k * (bw + gap) - bw / 2
    d.polygon([(x + skew, top), (x + skew + bw, top), (x + bw, bot), (x, bot)], fill=WHITE)
im = im.resize((1024, 1024), Image.LANCZOS)
im.resize((180, 180), Image.LANCZOS).save('icon.png'); im.resize((512, 512), Image.LANCZOS).save('icon-512.png'); im.resize((48, 48), Image.LANCZOS).save('favicon.png')
if len(sys.argv) > 1:
    pv = Image.new('RGB', (360 + 20 + 120 + 20 + 60, 360), (136, 136, 136)); pv.paste(im.resize((360, 360), Image.LANCZOS), (0, 0)); pv.paste(im.resize((120, 120), Image.LANCZOS), (380, 0)); pv.paste(im.resize((60, 60), Image.LANCZOS), (520, 0)); pv.save(sys.argv[1])
