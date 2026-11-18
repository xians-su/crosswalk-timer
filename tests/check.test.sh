#!/bin/bash
# The camera check against a recorded 16-minute sample (Wed 2026-11-18 18:00, plan 11):  bash tests/check.test.sh
# 1. the real timetable must be judged ok for all three crossings
# 2. a timetable shifted by 30 s must be flagged "adjusted" with an error near -30 (proves the check can fail)
# 3. a wrong expected lamp duration on the strict crossing must make the script exit 1
set -e; cd "$(dirname "$0")/.."; T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp check.py schedule.json calib.json "$T/"; S=tests/sample-wd-1800.csv
python3 "$T/check.py" "$S" > "$T/a.txt"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/a.txt') if l.strip().startswith('{')]
assert sorted(r['x'] for r in rows) == ['chengde', 'chifeng', 'zhongshan'], rows
assert all(r['status'] == 'ok' and abs(r['err']) <= 3 for r in rows), rows
print('ok   real timetable: all three crossings agree with the camera', [(r['x'], r['err']) for r in rows])
s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']: b['lamp']['on'] = (b['lamp']['on'] + 30) % b['cycle']
json.dump(s, open(T + '/schedule.json', 'w'), ensure_ascii=False)
PY
python3 "$T/check.py" "$S" > "$T/b.txt"
python3 - "$T" <<'PY'
import json, sys
T = sys.argv[1]; rows = [json.loads(l) for l in open(T + '/b.txt') if l.strip().startswith('{')]
assert len(rows) == 3 and all(r['status'] == 'adjusted' and -34 <= r['err'] <= -27 for r in rows), rows
print('ok   timetable shifted by 30 s is caught', [(r['x'], r['err']) for r in rows])
s = json.load(open(T + '/schedule.json'))
for x in s['crossings']:
    for b in x['bands']:
        b['lamp']['on'] = (b['lamp']['on'] - 30) % b['cycle']
        if x['id'] == 'chifeng': b['lamp']['len'] += 25
json.dump(s, open(T + '/schedule.json', 'w'), ensure_ascii=False)
PY
if python3 "$T/check.py" "$S" > /dev/null; then echo 'FAIL wrong lamp duration was not reported'; exit 1; else echo 'ok   wrong lamp duration on the strict crossing exits 1'; fi
