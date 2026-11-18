#!/bin/bash
# The camera check against a recorded 14-minute fine sample (Wed 2026-11-18 22:36, plan 08, 10 frames a second):  bash tests/check.test.sh
# 1. the real timetable must be judged ok, within 1 second, for both crossings the camera can measure
# 2. a timetable shifted by 30 s must be flagged with an error near -30: "adjusted" on the strict lamp, "drift" on the other
# 2b. a timetable shifted by only 1.5 s must also be caught (the whole point of fine sampling)
# 3. a wrong expected lamp duration on the strict crossing must make the script exit 1
set -e; cd "$(dirname "$0")/.."; T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp check.py schedule.json calib.json "$T/"; S=tests/sample-fine.csv
python3 "$T/check.py" "$S" > "$T/a.txt"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/a.txt') if l.strip().startswith('{')]
assert sorted(r['x'] for r in rows) == ['chifeng', 'zhongshan'], rows
assert all(r['status'] == 'ok' and r['fine'] and abs(r['err']) <= 1 and r['spread'] <= 0.6 for r in rows), rows
print('ok   real timetable: both crossings agree with the camera within 1 s', [(r['x'], r['err'], r['spread']) for r in rows])
s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']:
        if 'lamp' in b: b['lamp']['on'] = (b['lamp']['on'] + 30) % b['cycle']
json.dump(s, open(T + '/schedule.json', 'w'), ensure_ascii=False)
PY
python3 "$T/check.py" "$S" > "$T/b.txt"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/b.txt') if l.strip().startswith('{')]
assert len(rows) == 2 and all(-31 <= r['err'] <= -29 for r in rows), rows
assert {r['x']: r['status'] for r in rows} == {'chifeng': 'adjusted', 'zhongshan': 'drift'}, rows   # only the strict lamp may change the timetable
print('ok   timetable shifted by 30 s is caught', [(r['x'], r['err']) for r in rows])
s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']:
        if 'lamp' not in b: continue
        b['lamp']['on'] = (b['lamp']['on'] - 30) % b['cycle']
        if x['id'] == 'chifeng': b['lamp']['len'] += 25
json.dump(s, open(T + '/schedule.json', 'w'), ensure_ascii=False)
PY
python3 - "$T" <<'PY'
import json, sys, subprocess
T = sys.argv[1]; s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']:
        if 'lamp' in b:
            b['lamp']['on'] = (b['lamp']['on'] + 1.5) % b['cycle']
            if x['id'] == 'chifeng': b['lamp']['len'] -= 25
json.dump(s, open(T + '/s15.json', 'w'), ensure_ascii=False)
PY
cp "$T/schedule.json" "$T/keep.json"; cp "$T/s15.json" "$T/schedule.json"
python3 "$T/check.py" "$S" > "$T/c.txt" || true
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/c.txt') if l.strip().startswith('{')]
assert all(r['status'] in ('adjusted', 'drift') and -1.8 <= r['err'] <= -1.2 for r in rows), rows
print('ok   timetable shifted by only 1.5 s is caught', [(r['x'], r['err'], r['status']) for r in rows])
PY
cp "$T/keep.json" "$T/schedule.json"
if python3 "$T/check.py" "$S" > /dev/null; then echo 'FAIL wrong lamp duration was not reported'; exit 1; else echo 'ok   wrong lamp duration on the strict crossing exits 1'; fi
