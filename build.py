#!/usr/bin/env python3
"""crossings.json + plans.json + calib.json -> schedule.json, and the same data embedded in index.html as offline fallback.
Model per crossing: a cycle starts when (seconds-of-day - offset - K) % cycle == 0; the phases follow in order.
People may cross during phase `walk_phase`, from its start for (its length - clear) seconds.
K (seconds) comes from camera checks: calib.json {"K": 0, "per_plan": {"11": 1}, "checked": {...}} — these apply to the
first crossing (the one check.py measures); other crossings use K = 0 until they get their own check."""
import json, re, os
D = os.path.dirname(os.path.abspath(__file__))
sod = lambda s: int(s[:2]) * 3600 + int(s[3:]) * 60

def bands(P, X, C):
    out = []; w = X['walk_phase']
    for days in ('wd', 'we'):
        tab = P[days]
        for i, (frm, pid) in enumerate(tab):
            pl = P['plans'][pid]; K = C.get('per_plan', {}).get(pid, C.get('K', 0))
            to = sod(tab[i + 1][0]) if i + 1 < len(tab) else 86400
            # Taipei midnight in Unix seconds is a multiple of every cycle length in use (checked here)
            assert (8 * 3600) % pl['cycle'] == 0 and 86400 % pl['cycle'] == 0, f"cycle {pl['cycle']} breaks the midnight model"
            b = {'days': days, 'from': sod(frm), 'to': to, 'cycle': pl['cycle'], 'plan': pid,
                 'anchor': (pl['offset'] + K + sum(pl['p'][:w])) % pl['cycle'], 'red': pl['p'][w] - X['clear']}
            if X['code'] == 'SLWH710': b['lampRed'] = pl['p'][0] + pl['p'][2] + 2      # what check.py expects the camera to see
            out.append(b)
    return out

if __name__ == '__main__':
    XS = json.load(open(f'{D}/crossings.json')); PL = json.load(open(f'{D}/plans.json')); C = json.load(open(f'{D}/calib.json'))
    first = PL[XS[0]['code']]
    note = f"交工處時制表 {first['data_time'][:10]} 版・{XS[0]['name']}已用攝影機核對 {len(C.get('checked', {}))}/{len(first['plans'])} 套時制"
    sched = {'crossings': [{'id': X['id'], 'code': X['code'], 'name': X['name'], 'full': X['full'], 'walk': X['default_walk'],
                            'bands': bands(PL[X['code']], X, C if i == 0 else {})} for i, X in enumerate(XS)],
             'note': note, 'plan_time': first['data_time']}
    json.dump(sched, open(f'{D}/schedule.json', 'w'), ensure_ascii=False, indent=1)
    h = open(f'{D}/index.html').read()
    h, n = re.subn(r'/\*DATA\*/.*?/\*END\*/', lambda m: '/*DATA*/' + json.dumps(sched, ensure_ascii=False) + '/*END*/', h, 1, flags=re.S)
    assert n == 1, 'DATA marker missing in index.html'
    open(f'{D}/index.html', 'w').write(h); print([(x['name'], len(x['bands'])) for x in sched['crossings']], note)
