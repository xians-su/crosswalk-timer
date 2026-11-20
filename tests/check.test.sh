#!/bin/bash
# The camera check against a recorded 14-minute fine sample (Wed 2026-11-18 22:36, plan 08, 10 frames a second):  bash tests/check.test.sh
# 1. the real timetable must be judged ok, within 1 second, for both crossings the camera can measure
# 2. a timetable shifted by 30 s must be flagged "adjusted" with an error near -30 on both lamps
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
assert {r['x']: r['status'] for r in rows} == {'chifeng': 'adjusted', 'zhongshan': 'adjusted'}, rows   # both lamps are allowed to correct the timetable
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
# 4. the self-correction loop end to end: start from a timetable that is wrong (first crossing 1.5 s late, second 2 s early),
#    let the check apply its corrections, rebuild, and the same sample must then read ok on both
cp build.py crossings.json plans.json index.html "$T/"
echo '{"SLWH710": {"K": 0, "per_plan": {"08": 1.5}, "checked": {}}, "SLWH610": {"K": 0, "per_plan": {"08": -2.0}, "checked": {}}}' > "$T/calib.json"
echo '[]' > "$T/checks.json"
python3 "$T/build.py" > /dev/null
python3 "$T/check.py" "$S" --apply > "$T/d.txt" || true
python3 "$T/build.py" > /dev/null
python3 "$T/check.py" "$S" > "$T/e.txt"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rd = lambda f: [json.loads(l) for l in open(T + f) if l.strip().startswith('{')]
before, after, C = rd('/d.txt'), rd('/e.txt'), json.load(open(T + '/calib.json'))
assert {r['x']: r['status'] for r in before} == {'chifeng': 'adjusted', 'zhongshan': 'adjusted'}, before
assert all(r['status'] == 'ok' and abs(r['err']) <= 0.3 for r in after), after
assert abs(C['SLWH710']['per_plan']['08']) <= 0.3 and abs(C['SLWH610']['per_plan']['08']) <= 0.3, C
print('ok   a wrong timetable corrects itself:', [(r['x'], r['err']) for r in before], '->', [(r['x'], r['err']) for r in after])
PY
# 5. yellow read as red: the lamp comes on 3 s early but goes off on time (so it lasts 3 s longer than planned).
#    That is not a timetable shift and must not be "adjusted" (it was, twice, on 2026-11-19/20).
cp schedule.json "$T/schedule.json"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']:
        if 'lamp' in b: b['lamp']['on'] = (b['lamp']['on'] + 3) % b['cycle']; b['lamp']['len'] -= 3
json.dump(s, open(T + '/schedule.json', 'w'), ensure_ascii=False)
PY
python3 "$T/check.py" "$S" > "$T/f.txt" || true
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/f.txt') if l.strip().startswith('{')]
assert len(rows) == 2 and all(r['status'] == 'unclear' and r.get('note') == 'one edge only' and -3.4 <= r['err'] <= -2.8 for r in rows), rows
print('ok   lamp on 3 s early but off on time (yellow read as red) is not taken for a timetable shift', [(r['x'], r['err'], r['status']) for r in rows])
PY
