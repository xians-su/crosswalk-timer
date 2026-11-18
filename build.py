#!/usr/bin/env python3
"""crossings.json + plans.json + calib.json -> schedule.json, and the same data embedded in index.html as offline fallback.
Model per crossing: a cycle starts when (seconds-of-day - offset - K) % cycle == 0; the phases follow in order.
People may cross during phase `walk_phase` (per phase type where the plans differ), from its start until the
pedestrian signal's own stop time before the phase ends (行人停, at least min_clear seconds).
K (seconds) comes from camera checks, kept per crossing in calib.json: {"SLWH710": {"K": 0, "per_plan": {"11": 1}, "checked": {...}}, ...}."""
import json, re, os
D = os.path.dirname(os.path.abspath(__file__))
sod = lambda s: int(s[:2]) * 3600 + int(s[3:]) * 60

def bands(P, X, C, walk_phase=None):
    out = []
    for days in ('wd', 'we'):
        tab = P[days]
        for i, (frm, pid) in enumerate(tab):
            pl = P['plans'][pid]; K = C.get('per_plan', {}).get(pid, C.get('K', 0))
            wp = walk_phase if walk_phase is not None else X['walk_phase']
            w = wp if isinstance(wp, int) else wp[pl['type']]
            clear = max(pl['ped'][w][3], X['min_clear'])          # 行人停 seconds at the end of the phase, never less than min_clear
            to = sod(tab[i + 1][0]) if i + 1 < len(tab) else 86400
            # Taipei midnight in Unix seconds is a multiple of every cycle length in use (checked here)
            assert (8 * 3600) % pl['cycle'] == 0 and 86400 % pl['cycle'] == 0, f"cycle {pl['cycle']} breaks the midnight model"
            b = {'days': days, 'from': sod(frm), 'to': to, 'cycle': pl['cycle'], 'plan': pid, 'c0': round((pl['offset'] + K) % pl['cycle'], 1),   # c0: where each cycle starts
                 'anchor': round((pl['offset'] + K + sum(pl['p'][:w])) % pl['cycle'], 1), 'red': pl['p'][w] - clear - X.get('shorten', 0)}
            L = X.get('lamp')
            if L and walk_phase is None:             # what check.py expects the camera to see: when the lamp changes, and for how long
                ph = [w] if L['len_phases'] == 'walk' else L['len_phases']
                b['lamp'] = {'on': (b['anchor'] - L['lead']) % pl['cycle'], 'len': sum(pl['p'][i] for i in ph) + L['len_extra']}
            out.append(b)
    return out

if __name__ == '__main__':
    XS = json.load(open(f'{D}/crossings.json')); PL = json.load(open(f'{D}/plans.json')); C = json.load(open(f'{D}/calib.json'))
    if 'K' in C or 'per_plan' in C or 'checked' in C: C = {XS[0]['code']: C}        # old single-crossing format
    first = PL[XS[0]['code']]
    watched = [X for X in XS if X.get('lamp')]      # only crossings the camera check can measure count towards the progress note
    done = sum(len(C.get(X['code'], {}).get('checked', {})) for X in watched); total = sum(len(PL[X['code']]['plans']) for X in watched)
    note = f"交工處時制表 {first['data_time'][:10]} 版・攝影機已核對 {done}/{total} 套時制"
    def crossing(i, X):
        P, c = PL[X['code']], C.get(X['code'], {})
        out = {'id': X['id'], 'code': X['code'], 'name': X['name'], 'dir': X.get('dir', ''), 'full': X['full'], 'walk': X['default_walk'], 'bands': bands(P, X, c)}
        if X.get('lamp'): out['lamp'] = {k: X['lamp'][k] for k in ('roi', 'color', 'len_tol', 'strict', 'adjust', 'jitter') if k in X['lamp']}
        if X.get('approx'): out['approx'] = True       # timing varies from cycle to cycle: the page says so
        if X.get('options'):      # several crossings at one junction: the page shows a switch
            out['opts'] = [{'dir': o['dir'], 'bands': bands(P, X, c, o['walk_phase'])} for o in X['options']]
            for ob, bb in zip(out['opts'][0]['bands'], out['bands']):
                assert ob['anchor'] == bb['anchor'] and ob['red'] == bb['red'], 'the first option must be the default crossing'
        return out
    sched = {'crossings': [crossing(i, X) for i, X in enumerate(XS)],
             'note': note, 'plan_time': first['data_time']}
    json.dump(sched, open(f'{D}/schedule.json', 'w'), ensure_ascii=False, indent=1)
    h = open(f'{D}/index.html').read()
    h, n = re.subn(r'/\*DATA\*/.*?/\*END\*/', lambda m: '/*DATA*/' + json.dumps(sched, ensure_ascii=False) + '/*END*/', h, 1, flags=re.S)
    assert n == 1, 'DATA marker missing in index.html'
    open(f'{D}/index.html', 'w').write(h); print([(x['name'], len(x['bands'])) for x in sched['crossings']], note)
