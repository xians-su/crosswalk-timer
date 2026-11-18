#!/usr/bin/env python3
"""Compare sampled lamp data (南京西路 lamp, ROI B of logger.py) with schedule.json.
Usage: check.py SAMPLE.csv [--apply]
Per band covered by the sample:
  ok        timing agrees (|err - BIAS| <= TOL)
  adjusted  consistent drift on a clearly-read lamp -> calib.json per_plan K updated (with --apply)
  unclear   too few clean cycles (glare, traffic, camera moved) -> logged only
  mismatch  lamp read clearly but red length or cycle disagrees with the plan -> exit 1
FAIL looks like: 'mismatch' or 'adjusted' lines; a 30 s shifted schedule must produce 'adjusted'."""
import sys, json, os, datetime, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
BIAS, TOL = 3.5, 3.0   # BIAS: stream delay + detection lag of this method, measured 2026-11-18
TZ = datetime.timezone(datetime.timedelta(hours=8))

def red_runs(t, red, gap=4.0, minlen=20.0):
    """[(start, length)] of red periods, bridging dropouts shorter than `gap` seconds."""
    runs, start, last = [], None, None
    for ti, r in zip(t, red):
        if r:
            if start is None: start = ti
            elif ti - last > gap: runs.append((start, last - start)); start = ti
            last = ti
    if start is not None: runs.append((start, last - start))
    return [(s, l) for s, l in runs if l >= minlen]

def check(csv, sched):
    a = np.genfromtxt(csv, delimiter=',', usecols=[0, 6, 7]); t = a[:, 0]
    runs = red_runs(t, (a[:, 2] >= 3) & (a[:, 1] < 3))
    runs = [r for r in runs if r[0] > t[0] + 5 and r[0] + r[1] < t[-1] - 5]      # complete periods only
    res = []
    for b in sched['bands']:
        ev = []
        for s, l in runs:
            d = datetime.datetime.fromtimestamp(s, TZ); sod = d.hour * 3600 + d.minute * 60 + d.second
            if ('we' if d.weekday() >= 5 else 'wd') == b['days'] and b['from'] + 600 <= sod < b['to'] - b['cycle']:
                ev.append((s, l))                                                # skip 10 min after a plan change
        if not ev: continue
        on = np.array([s for s, _ in ev]); ln = np.array([l for _, l in ev])
        e = (on - (b['anchor'] - 2) + b['cycle'] / 2) % b['cycle'] - b['cycle'] / 2   # lamp turns red 2 s before the window
        good = np.abs(ln - b['lampRed']) <= 6                                    # red length as the plan says => right lamp, clean read
        r = {'days': b['days'], 'plan': b['plan'], 'from': b['from'], 'cycles': len(ev), 'clean': int(good.sum()),
             'red_len': round(float(np.median(ln)), 1), 'red_len_plan': b['lampRed']}
        if good.sum() < 3:
            r['status'] = 'mismatch' if len(ev) >= 4 and np.ptp(ln) <= 6 else 'unclear'
        else:
            eg = e[good]; core = eg[np.abs(eg - np.median(eg)) <= 2.5]          # ignore stray early/late detections
            r['err'] = round(float(np.median(core)) - BIAS, 1); r['spread'] = round(float(np.ptp(core)), 1); r['agree'] = int(len(core))
            if len(core) < 3 or len(core) < 0.6 * len(eg): r['status'] = 'unclear'
            else: r['status'] = 'ok' if abs(r['err']) <= TOL else 'adjusted'
        res.append(r)
    return res, t

if __name__ == '__main__':
    sched = json.load(open(f'{D}/schedule.json'))
    res, t = check(sys.argv[1], sched)
    when = datetime.datetime.fromtimestamp(t[0], TZ).strftime('%Y-%m-%d %H:%M')
    print(when, f'{len(t)} samples over {(t[-1]-t[0])/60:.0f} min')
    for r in res: print(' ', json.dumps(r, ensure_ascii=False))
    if not res: print('  no band covered (sample too short or right after a plan change)')
    if '--apply' in sys.argv:
        C = json.load(open(f'{D}/calib.json')); C.setdefault('per_plan', {}); C.setdefault('checked', {})
        for r in res:
            if r['status'] == 'adjusted':
                C['per_plan'][r['plan']] = C['per_plan'].get(r['plan'], C.get('K', 0)) + round(r['err'])
            if r['status'] in ('ok', 'adjusted'): C['checked'][r['plan']] = when
        json.dump(C, open(f'{D}/calib.json', 'w'), ensure_ascii=False, indent=1)
        p = f'{D}/checks.json'; log = json.load(open(p)) if os.path.exists(p) else []
        log += [dict(when=when, **r) for r in res] or [dict(when=when, status='no-band')]
        json.dump(log[-300:], open(p, 'w'), ensure_ascii=False, indent=0)
    sys.exit(1 if any(r['status'] == 'mismatch' for r in res) else 0)
