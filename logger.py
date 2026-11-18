#!/usr/bin/env python3
"""Sampler for Taipei traffic camera 415 (承德路一段 × 南京西路, looking east along 南京西路).
About once a second it fetches the newest video part, decodes one frame and counts lit green / red / yellow
pixels in five small boxes (ROIS) that sit on signal lamps — see docs/camera-lamps.jpg:
  A = 南京西路 lamp at 25 巷 (中山站 3・4 號出口)   B = 南京西路 lamp at 赤峰街 (the one check.py measures)
  C, D, E = the near 南京西路 lamp cluster at 承德路
Usage:  logger.py MINUTES OUT.csv          every frame (10 a second) for MINUTES — what the scheduled check runs
        logger.py MINUTES OUT.csv coarse   one frame a second for MINUTES
        logger.py                          one frame a second until stopped, data/YYYYMMDD.csv plus small crops
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
    if not out: os.makedirs(D, exist_ok=True)      # the data/ folder is not part of the repository
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

def fine(minutes, out):
    """Fine sampling for the scheduled check: every 1-second segment, all 10 frames, timed on the stream's own media clock.

    Why not simply stamp each frame with the time it was downloaded: download and decode times wander by a second or more.
    The stream carries a steady media clock (tfdt, 90 kHz), so each frame's position on that clock is exact to 0.1 s.
    Media time is tied to wall time by the smallest value of (moment the request was sent - media time of the segment's end)
    seen so far: that is the segment we asked for the instant it appeared, so what is left is only the camera-to-server
    delay, a constant that check.py removes as BIAS. Using the moment the request was *sent* keeps the result the same
    whether the sampler runs next to the camera server or on another continent."""
    import http.client, struct
    host, path = B.split('/')[2], '/' + '/'.join(B.split('/')[3:]) + '/'
    conn = [None]
    def req(name):
        for _ in (1, 2):
            try:
                if conn[0] is None: conn[0] = http.client.HTTPSConnection(host, timeout=8)
                sent = time.time(); conn[0].request('GET', path + name, headers={'User-Agent': 'Mozilla/5.0', 'Connection': 'keep-alive'})
                r = conn[0].getresponse(); return r.status, r.read(), sent
            except Exception:
                try: conn[0].close()
                except Exception: pass
                conn[0] = None
        return 0, b'', time.time()
    def tfdt(b):
        i = b.find(b'tfdt'); v = b[i + 4]
        return (struct.unpack('>Q', b[i+8:i+16])[0] if v == 1 else struct.unpack('>I', b[i+8:i+12])[0]) / 90000
    def newest():
        st, pl, _ = req('live.m3u8'); nums = re.findall(r'\nlive(\d+)\.mp4', pl.decode()) if st == 200 else []
        return int(nums[-1]) if nums else None
    st, init, _ = req('init.mp4'); assert st == 200, 'camera stream not reachable'
    n = newest(); assert n is not None, 'camera playlist is empty'
    t_end = time.time() + minutes * 60; tmp = out + '.mp4'; f = open(out, 'w')
    off, held, misses, segs, frames = None, [], 0, 0, 0
    def write(rows):
        for media, seg, cs in rows:
            ts = media + off; now = datetime.datetime.fromtimestamp(ts, TZ)
            f.write(','.join([f'{ts:.2f}', now.strftime('%H:%M:%S'), str(seg)] + [str(v) for v in cs]) + '\n')
    while time.time() < t_end:
        st, data, sent = req(f'live{n}.mp4')
        if st != 200 or len(data) < 2000:
            misses += 1; time.sleep(0.1)
            if misses > 50:                               # fell out of the window, or the numbering restarted
                m = newest(); n = m if m is not None else n; misses = 0
            continue
        misses = 0; t0 = tfdt(data); lag = sent - (t0 + 1.0)
        open(tmp, 'wb').write(init + data); c = cv2.VideoCapture(tmp); k = 0; rows = []
        while True:
            ok, im = c.read()
            if not ok: break
            if im.shape[:2] == (480, 720): rows.append((t0 + k / 10, n, [v for r in ROIS.values() for v in counts(im, r)]))
            k += 1
        c.release(); segs += 1; frames += len(rows); n += 1
        if off is None:                                   # hold the first minute, then stamp it with the best offset seen
            held.append((lag, rows))
            if len(held) >= 60:
                off = min(l for l, _ in held)
                for _, rs in held: write(rs)
                held = []
        else:
            off = min(off, lag); write(rows)
        if segs % 30 == 0: f.flush()
    if off is None and held:
        off = min(l for l, _ in held)
        for _, rs in held: write(rs)
    f.close()
    try: os.remove(tmp)
    except OSError: pass
    print(f'{frames} frames from {segs} segments')

if __name__ == '__main__':
    # logger.py MINUTES OUT.csv         -> fine sampling for MINUTES (what the scheduled check runs)
    # logger.py MINUTES OUT.csv coarse  -> one frame a second for MINUTES (light on the camera server; for multi-day logs)
    # logger.py                         -> one frame a second until stopped, daily CSV plus small crops under data/ (manual calibration)
    if len(sys.argv) > 3 and sys.argv[3] == 'coarse': main(float(sys.argv[1]), sys.argv[2])
    elif len(sys.argv) > 2: fine(float(sys.argv[1]), sys.argv[2])
    else: main()
