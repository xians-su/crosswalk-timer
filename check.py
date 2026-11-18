#!/usr/bin/env python3
"""Compare sampled lamp data (logger.py CSV) with schedule.json, for every crossing that has a `lamp` recipe in crossings.json.
Usage: check.py SAMPLE.csv [--apply]
For each crossing and each timing band covered by the sample:
  ok        the lamp changes when the timetable says (within TOL seconds after removing BIAS)
  adjusted  a strict lamp is read clearly (4+ agreeing cycles) and is consistently early/late -> that crossing's per_plan K in calib.json
            is updated (with --apply)
  drift     early/late by more than TOL, but the evidence is not strong enough to change the timetable -> logged only
  unclear   too few clean cycles (glare, traffic, camera moved) -> logged only
  mismatch  the lamp is read consistently but its duration disagrees with the plan -> logged; exit 1 if the crossing is marked strict
FAIL looks like: 'mismatch', 'adjusted' or 'drift' lines; a timetable shifted by 30 s must produce 'adjusted' (strict lamp) or 'drift' with err about -30."""
import sys, json, os, datetime, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
BIAS, TOL = 3.5, 3.0   # BIAS: stream delay + detection lag of this method, measured 2026-11-18
TZ = datetime.timezone(datetime.timedelta(hours=8))
COLS = {'A': 3, 'B': 6, 'C': 9, 'D': 12, 'E': 15}      # first CSV column (green count) of each sampling box; red is the next one

def runs_of(t, on, gap=4.0, minlen=20.0):
    """[(start, length)] of periods where `on` holds, bridging dropouts shorter than `gap` seconds."""
    runs, start, last = [], None, None
    for ti, r in zip(t, on):
        if r:
            if start is None: start = ti
            elif ti - last > gap: runs.append((start, last - start)); start = ti
            last = ti
    if start is not None: runs.append((start, last - start))
    return [(s, l) for s, l in runs if l >= minlen]
red_runs = runs_of      # earlier name, kept for anyone importing it

def check(csv, sched):
    res, t = [], None
    for X in sched['crossings']:
        L = X.get('lamp')
        if not L: continue
        c = COLS[L['roi']]; a = np.genfromtxt(csv, delimiter=',', usecols=[0, c, c + 1]); t = a[:, 0]
        lit = (a[:, 2] >= 3) & (a[:, 1] < 3) if L['color'] == 'red' else (a[:, 1] >= 3)
        runs = [r for r in runs_of(t, lit) if r[0] > t[0] + 5 and r[0] + r[1] < t[-1] - 5]      # complete periods only
        for b in X['bands']:
            ev = []
            for s, l in runs:
                d = datetime.datetime.fromtimestamp(s, TZ); sod = d.hour * 3600 + d.minute * 60 + d.second
                if ('we' if d.weekday() >= 5 else 'wd') == b['days'] and b['from'] + 600 <= sod < b['to'] - b['cycle']:
                    ev.append((s, l))                                                # skip 10 min after a plan change
            if not ev: continue
            on = np.array([s for s, _ in ev]); ln = np.array([l for _, l in ev])
            e = (on - b['lamp']['on'] + b['cycle'] / 2) % b['cycle'] - b['cycle'] / 2
            good = np.abs(ln - b['lamp']['len']) <= L['len_tol']                     # duration as the plan says => right lamp, clean read
            r = {'x': X['id'], 'days': b['days'], 'plan': b['plan'], 'from': b['from'], 'cycles': len(ev), 'clean': int(good.sum()),
                 'len': round(float(np.median(ln)), 1), 'len_plan': b['lamp']['len']}
            if good.sum() < 3:
                r['status'] = 'mismatch' if len(ev) >= 4 and np.ptp(ln) <= 6 else 'unclear'
            else:
                eg = e[good]; core = eg[np.abs(eg - np.median(eg)) <= L.get('jitter', 2.5)]   # ignore stray early/late detections
                r['err'] = round(float(np.median(core)) - BIAS, 1); r['spread'] = round(float(np.ptp(core)), 1); r['agree'] = int(len(core))
                if len(core) < 3 or len(core) < 0.6 * len(eg): r['status'] = 'unclear'
                elif abs(r['err']) <= TOL: r['status'] = 'ok'
                # correcting the timetable is only allowed on solid evidence: a strict lamp, at least 4 agreeing cycles, tight spread
                elif L.get('strict') and len(core) >= 4 and r['spread'] <= 2.5: r['status'] = 'adjusted'
                else: r['status'] = 'drift'
            res.append(r)
    return res, t

if __name__ == '__main__':
    sched = json.load(open(f'{D}/schedule.json'))
    res, t = check(sys.argv[1], sched)
    when = datetime.datetime.fromtimestamp(t[0], TZ).strftime('%Y-%m-%d %H:%M')
    print(when, f'{len(t)} samples over {(t[-1]-t[0])/60:.0f} min')
    for r in res: print(' ', json.dumps(r, ensure_ascii=False))
    if not res: print('  no band covered (sample too short or right after a plan change)')
    code = {X['id']: X['code'] for X in sched['crossings']}; strict = {X['id'] for X in sched['crossings'] if X.get('lamp', {}).get('strict')}
    if '--apply' in sys.argv:
        C = json.load(open(f'{D}/calib.json'))
        if 'K' in C or 'per_plan' in C or 'checked' in C: C = {sched['crossings'][0]['code']: C}      # old single-crossing format
        for r in res:
            c = C.setdefault(code[r['x']], {}); c.setdefault('K', 0); c.setdefault('per_plan', {}); c.setdefault('checked', {})
            if r['status'] == 'adjusted': c['per_plan'][r['plan']] = c['per_plan'].get(r['plan'], c['K']) + round(r['err'])
            if r['status'] in ('ok', 'adjusted'): c['checked'][r['plan']] = when
        json.dump(C, open(f'{D}/calib.json', 'w'), ensure_ascii=False, indent=1)
        p = f'{D}/checks.json'; log = json.load(open(p)) if os.path.exists(p) else []
        log += [dict(when=when, **r) for r in res] or [dict(when=when, status='no-band')]
        json.dump(log[-300:], open(p, 'w'), ensure_ascii=False, indent=0)
    sys.exit(1 if any(r['status'] == 'mismatch' and r['x'] in strict for r in res) else 0)
