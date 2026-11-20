// Timetable and weather logic, run straight from index.html without a browser:  node tests/logic.test.mjs
import fs from 'node:fs'; import assert from 'node:assert/strict'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const js = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const cut = (from, to) => { const a = js.indexOf(from), b = js.indexOf(to, a); assert(a >= 0 && b > a, 'cannot find ' + from); return js.slice(a, b); };
const DATA = JSON.parse(/\/\*DATA\*\/(.*?)\/\*END\*\//s.exec(html)[1]);
const src = [
  'let cross = 25; const manualOf = () => null, nudgeOf = () => 0, bandsOf = x => x.bands;',
  cut('function bandFor', 'const hms ='), cut('const hms =', '\n'), cut('const airLevel', '\n'), cut('const rainWord', '\n'), cut('function verdict', '/* 氣象署：特報'), cut('const uvLevel', '\n'),
  'return {bandFor, mod, windows, stateOf, leaveFrom, upcoming, hms, airLevel, rainWord, verdict, uvLevel};'].join('\n');
const F = new Function('DATA', src)(DATA);
const at = s => Date.parse(s) / 1000; let n = 0; const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };
const X = DATA.crossings.find(x => x.id === 'chifeng');

ok('schedule.json and the copy embedded in index.html are the same', () => {
  assert.deepEqual(DATA, JSON.parse(fs.readFileSync(path.join(root, 'schedule.json'), 'utf8')));
});
ok('every crossing covers the whole day on weekdays and weekends, with no gaps', () => {
  for (const x of DATA.crossings) for (const days of ['wd', 'we']) {
    const bs = x.bands.filter(b => b.days === days).sort((a, b) => a.from - b.from);
    assert.equal(bs[0].from, 0); assert.equal(bs[bs.length - 1].to, 86400);
    bs.slice(1).forEach((b, i) => assert.equal(b.from, bs[i].to));
    for (const b of bs){ assert(b.red >= 15 && b.red < b.cycle, `${x.id} plan ${b.plan}: crossing time ${b.red}s`); assert.equal(86400 % b.cycle, 0); }
  }
});
ok('weekday/weekend and the time of day pick the right band (Taipei time)', () => {
  assert.equal(F.bandFor(X.bands, at('2026-11-18T18:00:00+08:00')).plan, '11');      // Wednesday evening
  assert.equal(F.bandFor(X.bands, at('2026-11-18T20:00:00+08:00')).plan, '08');
  assert.equal(F.bandFor(X.bands, at('2026-11-21T10:00:00+08:00')).days, 'we');       // Saturday
  assert.equal(F.bandFor(X.bands, at('2026-11-22T23:59:59+08:00')).days, 'we');       // Sunday, last second
  assert.equal(F.bandFor(X.bands, at('2026-11-23T00:00:00+08:00')).days, 'wd');       // Monday, first second
});
const FLAT = {id: 'flat', bands: ['wd', 'we'].map(days => ({days, from: 0, to: 86400, cycle: 200, anchor: 15, red: 64, c0: 0, plan: 'x'}))};   // one plan all day
const t0 = 200 * 9000000 + 15;                                                          // a moment when its window opens
ok('state: may cross for `red` seconds from the anchor, then waits for the rest of the cycle', () => {
  const a = F.stateOf(FLAT, t0); assert.equal(a.go, true); assert.equal(a.left, 64); assert.equal(a.cycle, 200); assert.equal(a.shaky, false);
  assert.equal(F.stateOf(FLAT, t0 + 63).go, true); assert.equal(F.stateOf(FLAT, t0 + 64).go, false);
  assert.equal(F.stateOf(FLAT, t0 + 64).left, 136); assert.equal(F.stateOf(FLAT, t0 + 199).left, 1);
});
ok('departure: leave so that you arrive inside the window with time left to cross', () => {
  const lv = (t, walk) => F.leaveFrom(F.stateOf(FLAT, t).ws, t, walk);
  assert.equal(lv(t0 - 150, 90), 60);        // 90 s walk: leave 60 s from now, arrive as it opens
  assert.equal(lv(t0 - 60, 90), 0);          // arrive 30 s in, 34 s left, 25 s needed -> go now
  assert.equal(lv(t0 - 40, 90), 150);        // would arrive with 14 s left -> wait for the next one
  assert.equal(F.leaveFrom([[t0, t0 + 20, false]], t0, 30), null);                      // window shorter than the crossing itself
});
ok('upcoming times: within 30 minutes, in order, on each band\'s own cycle, also across a plan change', () => {
  for (const when of ['2026-11-18T18:00:10+08:00', '2026-11-18T19:50:00+08:00', '2026-11-21T23:45:00+08:00']) {
    const t = at(when), u = F.upcoming(X, t, 1800);
    assert(u.length >= 6, 'at least 6 times'); assert(u.every((v, i) => v > t && v <= t + 1800 && (i === 0 || v > u[i - 1])));
    for (const v of u){                         // each time sits on the rhythm of the plan in force, or of the plan just before it (its last cycle runs on after a change)
      const fits = b => { const off = F.mod(v - b.anchor, b.cycle); return off <= 1 || off >= b.cycle - 1; };
      assert(fits(F.bandFor(X.bands, v + 1)) || fits(F.bandFor(X.bands, v - 400)), 'misaligned at ' + F.hms(v));
    }
  }
});
ok('timetable change, as measured at 赤峰街口 on 2026-11-18 20:00: the old cycle finishes, one transitional cycle, then the new plan', () => {
  const T = at('2026-11-18T20:00:00+08:00'), hm = s => at('2026-11-18T' + s + '+08:00');
  // the camera saw the lamp go red at 20:01:15 (old plan's rhythm) and next at 20:05:02 (new plan), nothing in between
  const a = F.stateOf(X, hm('20:01:30')); assert.equal(a.go, true, 'old plan still running after 20:00'); assert.equal(a.shaky, false);
  for (const when of ['20:02:30', '20:02:45', '20:04:00']) assert.equal(F.stateOf(X, hm(when)).go, false, 'holding at ' + when);   // the new timetable alone would say "go" until 20:02:51
  const b = F.stateOf(X, hm('20:02:30')); assert.equal(Math.round(hm('20:02:30') + b.left), hm('20:05:01')); assert.equal(b.shaky, true);
  assert.equal(F.stateOf(X, hm('20:05:10')).go, true);
  const c = F.stateOf(X, hm('20:09:00')); assert.equal(c.shaky, false, 'back to normal from the second new cycle');
  const u = F.upcoming(X, T - 600, 1800).map(F.hms);
  assert(u.includes('19:57:55') && u.includes('20:01:15') && u.includes('20:08:01')); assert(!u.includes('20:05:01'), 'the transitional crossing is not offered');
  assert.equal(F.stateOf(X, at('2026-11-19T00:00:30+08:00')).shaky, false);          // midnight: same plan before and after, nothing changes
});
ok('timetable change at 17:00, as the camera saw it on 2026-11-19 and 11-20 at both crossings: the new plan already gives one crossing inside the transitional cycle', () => {
  const hm = s => at('2026-11-20T' + s + '+08:00'), Z = DATA.crossings.find(x => x.id === 'zhongshan');
  // 赤峰街口: lamp red at 17:01:51 (old plan), 17:04:33 and 17:07:53 (new plan); the crossing opens 2 s after the lamp
  const a = F.stateOf(X, hm('17:03:30')); assert.equal(a.go, false); assert.equal(Math.round(hm('17:03:30') + a.left), hm('17:04:35')); assert.equal(a.shaky, false);
  assert.equal(F.stateOf(X, hm('17:02:00')).go, true, 'old plan runs its last cycle'); assert.equal(F.stateOf(X, hm('17:05:00')).go, true);
  assert(F.upcoming(X, hm('17:00:00'), 600).map(F.hms).includes('17:04:35'));
  const z = F.stateOf(Z, hm('17:03:30')); assert.equal(Math.round(hm('17:03:30') + z.left), hm('17:04:26'));
  // 23:00 at 赤峰街口: only 29 s between the end of the old cycle and the new plan's slot -> the camera saw nothing there, so none is listed
  assert(!F.upcoming(X, at('2026-11-19T23:00:00+08:00'), 400).map(F.hms).includes('23:03:20'));
});
ok('rain wording by forecast amount, and the umbrella verdict', () => {
  assert.deepEqual([0.2, 0.5, 4.9, 5, 14.9, 15].map(F.rainWord), ['毛毛雨', '小雨', '小雨', '中雨', '中雨', '大雨']);
  const t = 1e9, R = mm => ({nowcast: {mm, at: t - 600, time: '12:00'}, past: null}), v = (mm, extra = {}) => F.verdict({wet: false, msg: '不用帶傘', warn: '', rainingNow: false, cells: [], ...extra}, R(mm), t);
  assert.equal(v(0).msg, '一小時內不會下雨'); assert.equal(v(0).wet, false);
  assert.equal(v(0.2).msg, '一小時內可能有毛毛雨，建議帶傘'); assert.equal(v(3).msg, '一小時內有小雨，帶傘'); assert.equal(v(20).msg, '一小時內有大雨，帶傘');
  assert.equal(v(0, {rainingNow: true}).msg, '正在下雨，帶傘');
  assert.equal(v(0, {brief: {uv: 9}}).msg, '紫外線過量級，建議遮陽'); assert.equal(v(0, {brief: {uv: 7}}).msg, '一小時內不會下雨');
  assert.equal(v(3, {brief: {uv: 9}}).msg, '一小時內有小雨，帶傘');                    // rain wins over sun
  const stale = F.verdict({wet: true, msg: '可能下雨，建議帶傘', warn: '', rainingNow: false, cells: []}, {nowcast: {mm: 0, at: t - 4000, time: 'x'}, past: null}, t);
  assert.equal(stale.msg, '可能下雨，建議帶傘');                                         // radar data older than 45 min is ignored
});
ok('UV and air-quality levels', () => {
  assert.deepEqual([2, 3, 6, 8, 11].map(F.uvLevel), ['低量級', '中量級', '高量級', '過量級', '危險級']);
  assert.deepEqual([50, 51, 101, 151, 201, 301].map(F.airLevel), ['良好', '普通', '對敏感族群不健康', '不健康', '非常不健康', '危害']);
});
console.log(`\n${n} groups passed`);
