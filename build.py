#!/usr/bin/env python3
"""plans.json + calib.json -> schedule.json, and the same data embedded in index.html as offline fallback.
Model: a cycle starts when (seconds-of-day - offset - K) % cycle == 0, then phase 1, phase 2
(南京西路 green), phase 3 (赤峰街 green = may cross). The crossing window starts at phase-3 start and
lasts p3 - CLEAR seconds. K (seconds) comes from camera checks: calib.json {"K": 0, "per_plan": {"11": 1}}."""
import json, re, os
D = os.path.dirname(os.path.abspath(__file__)); CLEAR = 6
sod = lambda s: int(s[:2]) * 3600 + int(s[3:]) * 60

def bands(P, C):
    out = []
    for days in ('wd', 'we'):
        tab = P[days]
        for i, (frm, pid) in enumerate(tab):
            pl = P['plans'][pid]; K = C.get('per_plan', {}).get(pid, C.get('K', 0))
            to = sod(tab[i + 1][0]) if i + 1 < len(tab) else 86400
            # Taipei midnight in Unix seconds is a multiple of every cycle length in use (checked below)
            assert (8 * 3600) % pl['cycle'] == 0 and 86400 % pl['cycle'] == 0, f"cycle {pl['cycle']} breaks the midnight model"
            anchor = (pl['offset'] + K + pl['p'][0] + pl['p'][1]) % pl['cycle']
            out.append({'days': days, 'from': sod(frm), 'to': to, 'cycle': pl['cycle'], 'anchor': anchor,
                        'red': pl['p'][2] - CLEAR, 'plan': pid, 'lampRed': pl['p'][0] + pl['p'][2] + 2})
    return out

if __name__ == '__main__':
    P = json.load(open(f'{D}/plans.json')); C = json.load(open(f'{D}/calib.json'))
    checked = sorted(C.get('checked', {}))
    note = f"臺北市交工處時制表 {P['data_time'][:10]} 版；已用路口攝影機核對 {len(checked)}/{len(P['plans'])} 套時制"
    sched = {'bands': bands(P, C), 'note': note, 'plan_time': P['data_time']}
    json.dump(sched, open(f'{D}/schedule.json', 'w'), ensure_ascii=False, indent=1)
    h = open(f'{D}/index.html').read()
    h = re.sub(r'/\*BANDS\*/.*?/\*END\*/', lambda m: '/*BANDS*/' + json.dumps(sched['bands']) + '/*END*/', h, 1, re.S)
    h = re.sub(r'/\*SRC\*/.*?/\*END\*/', lambda m: '/*SRC*/' + json.dumps(note, ensure_ascii=False) + '/*END*/', h, 1, re.S)
    open(f'{D}/index.html', 'w').write(h); print(len(sched['bands']), 'bands;', note)
