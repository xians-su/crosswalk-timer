#!/usr/bin/env python3
"""Download the official timing-plan PDF of every crossing in crossings.json and write plans.json
({code: plan}). Exits non-zero (so the workflow fails and GitHub notifies) if a layout no longer matches
what the timetable model assumes: Mon-Fri identical, Sat=Sun, the expected number of phases summing to the cycle."""
import json, os, re, subprocess, sys, urllib.request
D = os.path.dirname(os.path.abspath(__file__))
URL = 'https://www.ttcx.dot.gov.taipei/cpt/api/TimingPlan/pdf/'
PLAN = re.compile(r'(?:^|\s)(\d{2})\s+(\d{2,3})\s+(\d{1,3})\s+(\d)\s+([0-9A-F]{2})\s+((?:\d+\s*)+)$')

def parse(txt, X):
    wd, we, plans, times, data_time, last = [], [], {}, None, None, None
    def ped(text):   # the line under a plan: 黃,全紅,行人閃,行人停 for each phase
        g = re.findall(r'(\d+),(\d+),(\d+),(\d+)', text)
        if g and last and 'ped' not in plans[last]: plans[last]['ped'] = [[int(v) for v in t] for t in g]
    for line in txt.splitlines():
        m = re.search(r'資料時間：([\d\- :]+)', line)
        if m: data_time = m.group(1).strip()
        s = line.strip()
        if s.startswith('時間'):
            times = re.findall(r'\b\d{2}:\d{2}\b', s)
            rest = s.split(times[-1])[-1] if times else s
            m = PLAN.search(rest)
        elif s.startswith('時制') and times:
            ids = s.split()[1:1 + len(times)]
            assert all(re.fullmatch(r'\d{2}', i) for i in ids), f'bad plan ids: {s}'
            cols = {7: (range(5), range(5, 7)), 5: (range(5), []), 2: ([], range(2))}[len(times)]
            for tab, idx in ((wd, cols[0]), (we, cols[1])):
                pairs = {(times[i], ids[i]) for i in idx}
                assert len(pairs) <= 1, f'days differ within weekday/weekend group: {s}'
                tab.extend(pairs)
            ped(s); times = None; continue
        elif ',' not in s and not s.startswith('路口'):
            m = PLAN.search(s)
        else: m = None; ped(s)
        if m:
            pid, cyc, off, _, typ, ph = m.groups(); p = [int(x) for x in ph.split()]
            assert len(p) in X['phases'] and sum(p) == int(cyc), f'plan {pid}: phases {p} vs cycle {cyc}'
            plans[pid] = {'cycle': int(cyc), 'offset': int(off), 'type': typ, 'p': p}; last = pid
    for tab in (wd, we):
        tab.sort(); assert tab and tab[0][0] == '00:00', 'table must start at 00:00'
        # merge consecutive rows with the same plan
        tab[:] = [list(r) for i, r in enumerate(tab) if i == 0 or r[1] != tab[i - 1][1]]
        assert all(pid in plans for _, pid in tab), 'table refers to an unknown plan'
    for pid, pl in plans.items(): assert len(pl.get('ped', [])) == len(pl['p']), f'plan {pid}: pedestrian timings missing'
    assert data_time and len(plans) >= 3
    return {'source': URL + X['code'], 'data_time': data_time, 'intersection': f"{X['full']} ({X['code']})", 'wd': wd, 'we': we,
            'plans': dict(sorted(plans.items()))}

if __name__ == '__main__':
    # parse_plan.py            -> download every crossing's PDF
    # parse_plan.py DIR        -> read DIR/<code>.pdf instead (tests)
    old = json.load(open(f'{D}/plans.json')) if os.path.exists(f'{D}/plans.json') else {}
    new, changed = {}, False
    for X in json.load(open(f'{D}/crossings.json')):
        pdf = os.path.join(sys.argv[1], X['code'] + '.pdf') if len(sys.argv) > 1 else f"/tmp/{X['code']}.pdf"
        if len(sys.argv) <= 1:
            req = urllib.request.Request(URL + X['code'], headers={'User-Agent': 'Mozilla/5.0'})
            open(pdf, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
        n = parse(subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout, X)
        o = old.get(X['code'], {}); same = all(o.get(k) == n[k] for k in ('wd', 'we', 'plans'))
        print(X['code'], 'official plan', n['data_time'], 'unchanged' if same else 'CHANGED')
        changed |= not same or o.get('data_time') != n['data_time']; new[X['code']] = n
    if changed: json.dump(new, open(f'{D}/plans.json', 'w'), ensure_ascii=False, indent=1)
