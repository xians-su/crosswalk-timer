#!/usr/bin/env python3
"""Sampler for Taipei traffic camera 415 (承德路一段 × 南京西路, looking east along 南京西路).
About once a second it fetches the newest video part, decodes one frame and counts lit green / red / yellow
pixels in five small boxes (ROIS) that sit on signal lamps — see docs/camera-lamps.jpg:
  A = 南京西路 lamp at 25 巷 (中山站 3・4 號出口)   B = 南京西路 lamp at 赤峰街 (the one check.py measures)
  C, D, E = the near 南京西路 lamp cluster at 承德路
Usage:  logger.py MINUTES OUT.csv   sample for MINUTES (what the scheduled check runs)
        logger.py                   run until stopped, writing data/YYYYMMDD.csv plus small crops (manual calibration)
CSV columns: unix time, HH:MM:SS, video segment, then green,red,yellow counts for A, B, C, D, E."""
import cv2, time, re, os, sys, urllib.request, datetime, numpy as np
B = 'https://jtmctrafficcctv3.gov.taipei/NVR/4309f60c-3f97-41ea-8598-84a0dd149f87'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TZ = datetime.timezone(datetime.timedelta(hours=8))
ROIS = {'A': (383, 148, 8, 10), 'B': (392, 150, 8, 8), 'C': (421, 152, 7, 8),
        'D': (422, 160, 6, 6), 'E': (430, 166, 6, 6)}
CROP = (300, 100, 180, 100)  # x,y,w,h

def get(u):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(r, timeout=8).read()

def counts(im, roi):
    x, y, w, h = roi
    hsv = cv2.cvtColor(im[y:y+h, x:x+w], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    lit = (S > 70) & (V > 140)
    g = int((lit & (H >= 55) & (H <= 100)).sum())
    r = int((lit & ((H <= 8) | (H >= 170))).sum())
    yl = int((lit & (H >= 12) & (H <= 35)).sum())
    return g, r, yl

def main(minutes=None, out=None):
    init, init_t, seen = None, 0, None
    tmp = (out + '.mp4') if out else os.path.join(D, 't.mp4')
    t_end = time.time() + minutes * 60 if minutes else None
    while t_end is None or time.time() < t_end:
        t0 = time.time()
        try:
            if init is None or t0 - init_t > 600:
                init, init_t = get(B + '/init.mp4'), t0
            pl = get(B + '/live.m3u8').decode()
            parts = re.findall(r'URI="(live(\d+)\.(\d)\.mp4)",INDEPENDENT=YES', pl)
            name, seg, _ = parts[-1]
            if seg != seen:
                seen = seg
                data = get(B + '/' + name)
                ts = time.time()
                open(tmp, 'wb').write(init + data)
                c = cv2.VideoCapture(tmp); ok, im = c.read(); c.release()
                if ok and im.shape[:2] == (480, 720):
                    now = datetime.datetime.fromtimestamp(ts, TZ)
                    row = [f'{ts:.2f}', now.strftime('%H:%M:%S'), seg]
                    for k in ROIS:
                        row += map(str, counts(im, ROIS[k]))
                    with open(out or os.path.join(D, now.strftime('%Y%m%d') + '.csv'), 'a') as f:
                        f.write(','.join(row) + '\n')
                    if not out:
                        x, y, w, h = CROP
                        cd = os.path.join(D, 'crops', now.strftime('%Y%m%d/%H'))
                        os.makedirs(cd, exist_ok=True)
                        cv2.imwrite(os.path.join(cd, now.strftime('%M%S') + '.jpg'), im[y:y+h, x:x+w],
                                    [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if now.minute % 10 == 0 and now.second < 2:
                            cv2.imwrite(os.path.join(D, 'crops', now.strftime('%Y%m%d/full_%H%M.jpg')), im)
                else:
                    print(time.strftime('%F %T'), 'decode fail', ok, flush=True)
        except Exception as e:
            print(time.strftime('%F %T'), 'err', repr(e)[:120], flush=True)
            init = None; time.sleep(2)
        time.sleep(max(0.05, 0.5 - (time.time() - t0)))

if __name__ == '__main__':
    # logger.py                 -> run forever, daily CSV + crops under data/ (calibration on a server)
    # logger.py MINUTES OUT.csv -> sample for MINUTES into OUT.csv (scheduled check)
    main(float(sys.argv[1]), sys.argv[2]) if len(sys.argv) > 2 else main()
