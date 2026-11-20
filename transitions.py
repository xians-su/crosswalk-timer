#!/usr/bin/env python3
"""Check the timetable-change rule against camera logs.  Usage: transitions.py LOG.csv [LOG.csv ...]

The rule the page uses (see windows() in index.html): at a timetable change the signal finishes the cycle of the old
plan that is in progress, runs one transitional cycle, and from the second cycle on follows the new plan exactly.
The transitional cycle is not predictable (measured 5 to 21 s away from "hold until the new plan's next cycle start").
For every change inside the logs, and every crossing with a `lamp`, this prints the lamp events the camera saw from
7 minutes before to 15 minutes after, each with its distance from what the rule predicts. Small numbers = the rule holds.
Coarse logs (one frame a second) are good to about +-1.5 s, fine logs to about +-0.2 s."""
import sys, json, os, datetime, numpy as np, check
D = os.path.dirname(os.path.abspath(__file__)); TZ = check.TZ
mod = lambda v, n: ((v % n) + n) % n
hm = lambda ts: datetime.datetime.fromtimestamp(ts, TZ).strftime('%m-%d %H:%M:%S')

def band_at(bands, ts):
    d = datetime.datetime.fromtimestamp(ts, TZ); sod = d.hour * 3600 + d.minute * 60 + d.second; days = 'we' if d.weekday() >= 5 else 'wd'
    return next(b for b in bands if b['days'] == days and b['from'] <= sod < b['to']), ts - sod

def main(files):
    S = json.load(open(f'{D}/schedule.json')); worst = {}
    for X in S['crossings']:
        L = X.get('lamp')
        if not L: continue
        c = check.COLS[L['roi']]; a = np.concatenate([np.genfromtxt(f, delimiter=',', usecols=[0, c, c + 1]) for f in files]); a = a[np.argsort(a[:, 0])]; t = a[:, 0]
        M = check.FINE if np.median(np.diff(t)) < 0.5 else check.COARSE
        lit = (a[:, 2] >= 3) & (a[:, 1] < 3) if L['color'] == 'red' else (a[:, 1] >= 3)
        runs = check.runs_of(t, lit); day = band_at(X['bands'], t[0])[1]
        while day < t[-1]:
            for frm in sorted({b['from'] for b in X['bands']}):
                T = day + frm
                if not (t[0] + 430 < T < t[-1] - 900): continue
                new, _ = band_at(X['bands'], T + 1); old, _ = band_at(X['bands'], T - 1)
                if (old['cycle'], old['anchor'], old['red']) == (new['cycle'], new['anchor'], new['red']): continue
                s_old = T + mod(old['c0'] - T, old['cycle']); s_new = s_old + mod(new['c0'] - s_old, new['cycle'])
                pred = [(k + mod(old['lamp']['on'] - k, old['cycle']), 'old plan') for k in np.arange(s_old - 5 * old['cycle'], s_old - 1, old['cycle'])]
                pred += [(k + mod(new['lamp']['on'] - k, new['cycle']), 'new plan') for k in np.arange(s_new, T + 900, new['cycle'])]
                early = s_new + mod(new['lamp']['on'] - s_new, new['cycle']) - new['cycle']      # the new plan's slot inside the transitional cycle
                if early + (new['anchor'] - new['lamp']['on']) % new['cycle'] - s_old >= 75: pred.append((early, 'new plan'))   # GAP_MIN in index.html
                print(f"\n{X['name']}  {hm(T)}  plan {old['plan']} -> {new['plan']} (cycle {old['cycle']} -> {new['cycle']} s): old cycle ends {hm(s_old)[6:]}, new plan starts {hm(s_new)[6:]}, hold {s_new - s_old:.0f} s")
                first_new = True
                for s, _ in [r for r in runs if T - 420 <= r[0] <= T + 900]:
                    e, tag = min(((s - p - M['bias'], tag) for p, tag in pred), key=lambda v: abs(v[0]))
                    note = ''
                    if tag == 'new plan' and first_new: note = '   <- first cycle of the new plan'; first_new = False
                    elif tag == 'old plan' and s > T: note = '   <- old plan still running after the change'
                    if not note or 'old plan' in note: worst[X['name']] = max(worst.get(X['name'], 0), abs(e))
                    print(f"   lamp at {hm(s)[6:]}   {e:+5.1f} s from the rule ({tag}){note}")
            day += 86400
    print('\nlargest miss, leaving out the first cycle of each new plan:', {k: round(v, 1) for k, v in worst.items()})

if __name__ == '__main__':
    main(sys.argv[1:])
