#!/usr/bin/env python3
"""Home-screen icon: four figures crossing a zebra crossing, each caught at a different moment of the stride, in the company palette."""
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

# four different moments of a stride: (front knee, front foot, back knee, back foot, back elbow, back hand, front elbow, front hand),
# each as (x, y) in units of the figure's height, measured from the point under the hips
POSES = {
 'reach':  ((.13,-.23), (.235, 0),   (-.10,-.22), (-.25,-.035), (-.095,-.585), (-.19,-.50), (.13,-.60),  (.225,-.555)),
 'pass':   ((.17,-.245), (.085,-.085), (-.03,-.215), (-.065, 0),  (-.10,-.59), (-.155,-.475), (.12,-.59), (.20,-.505)),
 'swing':  ((.10,-.215), (.20, 0),   (-.12,-.205), (-.235,-.03), (.11,-.585),  (.19,-.49),  (-.115,-.60), (-.215,-.565)),
 'push':   ((.10,-.215), (.20, 0),  (-.05,-.215), (-.20,-.10), (-.075,-.585), (-.14,-.475), (.13,-.60), (.22,-.53)),
}
def walker(cx, base, h, col, pose):
    wd = round(h * 0.125); P = lambda v: (cx + v[0] * h, base + v[1] * h - (wd / 2 if v[1] == 0 else 0))
    kf, ff, kb, fb, eb, hb, ef, hf = (P(v) for v in POSES[pose])
    neck = (cx + h * 0.045, base - h * 0.77); hip = (cx - h * 0.015, base - h * 0.43); sh = (cx + h * 0.035, base - h * 0.71); aw = round(wd * 0.82)
    limb(sh, eb, aw, col); limb(eb, hb, aw, col)                                 # far arm first so the body overlaps it
    limb(hip, kb, wd, col); limb(kb, fb, wd, col)
    limb(neck, hip, round(wd * 1.3), col)
    limb(hip, kf, wd, col); limb(kf, ff, wd, col)
    limb(sh, ef, aw, col); limb(ef, hf, aw, col)
    r = h * 0.1; hc = (cx + h * 0.075, base - h * 0.905)
    d.ellipse((hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r), fill=col)

for i, (col, pose, k) in enumerate(((CYAN, 'reach', 1.0), (GREEN, 'pass', 1.05), (CYAN, 'swing', 0.97), (GREEN, 'push', 1.02))):
    walker(138 + i * 240, top + 8, 440 * k, col, pose)
im.resize((180, 180), Image.LANCZOS).save('icon.png'); im.resize((512, 512), Image.LANCZOS).save('icon-512.png'); im.resize((48, 48), Image.LANCZOS).save('favicon.png')
import sys
if len(sys.argv) > 1:
    pv = Image.new('RGB', (360 + 20 + 120 + 20 + 60, 360), (136, 136, 136)); pv.paste(im.resize((360, 360), Image.LANCZOS), (0, 0)); pv.paste(im.resize((120, 120), Image.LANCZOS), (380, 0)); pv.paste(im.resize((60, 60), Image.LANCZOS), (520, 0)); pv.save(sys.argv[1])
