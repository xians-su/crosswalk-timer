#!/usr/bin/env python3
"""Browser test of the page: python3 tests/page.test.py   (needs: pip install playwright && playwright install webkit chromium)
Serves the repository folder on a local port, blocks every outside request (so no weather or camera traffic),
and drives the page the way a phone would. Prints one line per check and exits non-zero on the first failure."""
import http.server, os, socketserver, sys, threading, functools
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT)); PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
n = 0
def ok(name, cond, detail=''):
    global n
    if not cond: print('FAIL', name, detail); sys.exit(1)
    n += 1; print('ok  ', name)

def new_page(browser, width=393, **kw):
    ctx = browser.new_context(viewport={'width': width, 'height': 760}, locale='zh-TW', timezone_id='Asia/Taipei', **kw)
    ctx.route('**/*', lambda r: r.continue_() if '127.0.0.1' in r.request.url else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200); return ctx, pg, errs

EDGE = {'position': {'x': 335, 'y': 22}}     # tap near the arrow: the middle of the third card's title row is its direction switch
OPEN = "[...document.querySelectorAll('.x')].map(x=>x.classList.contains('open'))"
NAMES = "[...document.querySelectorAll('.x .xname span')].map(e=>e.textContent)"
FIRE = "(t,x,y)=>{const e=new Event(t,{bubbles:true,cancelable:true}); Object.defineProperty(e,'touches',{value:y===null?[]:[{clientX:x,clientY:y}]}); window.dispatchEvent(e)}"

with sync_playwright() as p:
    wk = p.webkit.launch()
    # --- layout
    for w in (320, 393):
        ctx, pg, errs = new_page(wk, w, is_mobile=True, has_touch=True)
        ok(f'no script errors and no sideways scrolling at {w} px', not errs and pg.evaluate('document.documentElement.scrollWidth') == w, str(errs))
        ok(f'three crossings are shown at {w} px', pg.evaluate("document.querySelectorAll('.x').length") == 3)
        ctx.close()
    ctx, pg, errs = new_page(wk, is_mobile=True, has_touch=True)
    # --- cards: one open at most, all may be closed
    ok('first crossing starts open', pg.evaluate(OPEN) == [True, False, False])
    pg.tap('.x.open .xhead'); pg.wait_for_timeout(250); ok('tapping the open card closes it', pg.evaluate(OPEN) == [False, False, False])
    pg.tap('.x >> nth=1 >> .xhead'); pg.wait_for_timeout(250); pg.tap('.x >> nth=2 >> .xhead'); pg.wait_for_timeout(250)
    ok('opening another card closes the previous one', pg.evaluate(OPEN) == [False, False, True])
    # --- walking time is per crossing and remembered
    before = pg.evaluate("[...document.querySelectorAll('.walkstep output')].map(e=>e.textContent)")
    pg.tap('.x.open .up'); pg.wait_for_timeout(200); after = pg.evaluate("[...document.querySelectorAll('.walkstep output')].map(e=>e.textContent)")
    ok('walking time changes only on its own crossing', after[:2] == before[:2] and after[2] != before[2], f'{before} -> {after}')
    # --- direction switch
    dirs = pg.evaluate("[...document.querySelectorAll('.x.open .opts button')].map(b=>b.textContent)")
    ok('the third crossing offers two directions', len(dirs) == 2, str(dirs))
    # --- choosing a later crossing time
    pg.tap('.x.open .nexts button >> nth=1'); pg.wait_for_timeout(400)
    st = pg.evaluate("(()=>{const x=document.querySelector('.x.open'); return [x.classList.contains('pin'), x.querySelector('.secs').textContent, !x.querySelector('.live').hidden, x.querySelector('.xsum b').textContent]})()")
    ok('tapping a later time switches the card to counting down to it', st[0] and st[2] and '還有' in st[3], str(st))
    import re
    sub = pg.evaluate("document.querySelector('.x.open .sub').textContent")
    ok('a chosen time always shows its unit', bool(re.search(r'還有 (\d+ 秒|\d+:\d\d)$', st[3])) and bool(re.search(r'(^|\d )秒後可以過$', sub)), str([st[3], sub]))
    # --- a manual press that agrees with the timetable keeps the timetable; one that is seconds away replaces it
    cal = pg.evaluate('''(()=>{ const keepSel = sel, keepClk = CLK, x = DATA.crossings[0]; sel = x.id; const out = [];
      for (const shift of [0.4, 5]){ const t = now(), b = bandFor(bandsOf(x), t), d = mod(t - b.anchor + b.cycle/2, b.cycle) - b.cycle/2; CLK += shift - d;
        document.getElementById('sync').click(); out.push([!!manualOf(x, now()), document.getElementById('calNote').textContent]); }
      document.getElementById('clear').click(); localStorage.removeItem('xw_cal_' + x.id); sel = keepSel; CLK = keepClk; labels(); render(); return out })()''')
    ok('a press within 1 s of the timetable keeps the timetable', cal[0][0] is False and '照時刻表走' in cal[0][1], str(cal[0]))
    ok('a press 5 s away switches to the press', cal[1][0] is True and '照時刻表走' not in cal[1][1], str(cal[1]))
    pg.tap('.x.open .xhead', **EDGE); pg.wait_for_timeout(250)
    ok('the collapsed row also follows the chosen time', pg.evaluate("document.querySelectorAll('.x')[2].classList.contains('pin')"))
    pg.tap('.x >> nth=2 >> .xhead', **EDGE); pg.wait_for_timeout(250); pg.tap('.x.open .opts button >> nth=1'); pg.wait_for_timeout(300)
    ok('switching direction returns the card to live', not pg.evaluate("document.querySelector('.x.open').classList.contains('pin')"))
    pg.tap('.x.open .nexts button >> nth=0'); pg.wait_for_timeout(300); pg.tap('.x.open .live'); pg.wait_for_timeout(300)
    ok('the back-to-live button clears the chosen time', not pg.evaluate("document.querySelector('.x.open').classList.contains('pin')"))
    pg.tap('.x.open .nexts button >> nth=0'); pg.wait_for_timeout(300)
    pg.evaluate("(()=>{for(const k of Object.keys(localStorage)) if(k.startsWith('xw_pin_') && localStorage[k]!=='0') localStorage[k]=JSON.stringify(Math.floor(Date.now()/1000)-5)})()"); pg.wait_for_timeout(1300)
    ok('a chosen time expires by itself once it has started', not pg.evaluate("document.querySelector('.x.open').classList.contains('pin')"))
    # --- settings: memo switch, keep-awake switch, theme
    ok('memo is hidden and keep-awake is off by default', pg.evaluate("document.getElementById('memo').hidden") and pg.evaluate("document.getElementById('awakeOn').getAttribute('aria-checked')") == 'false')
    pg.tap('.x.open .xhead', **EDGE); pg.tap('#more > summary'); pg.wait_for_timeout(200); pg.tap('#adv > summary'); pg.wait_for_timeout(250); pg.tap('#memoOn'); pg.wait_for_timeout(250)
    pg.fill('#memoText', '識別證'); pg.wait_for_timeout(200)
    ok('memo appears when switched on and shows a clear button once it has text', not pg.evaluate("document.getElementById('memo').hidden") and not pg.evaluate("document.getElementById('memoClear').hidden"))
    modes = []
    for _ in range(3): pg.tap('#theme'); modes.append(pg.evaluate("document.documentElement.getAttribute('data-theme')"))
    ok('the theme button cycles light, dark, then back to following the system', modes == ['light', 'dark', None], str(modes))
    # --- everything above is remembered
    pg.goto('about:blank'); pg.goto(URL); pg.wait_for_timeout(1000)
    kept = pg.evaluate("[document.getElementById('memoText').value, [...document.querySelectorAll('.walkstep output')].map(e=>e.textContent)[2], document.querySelector('.x.open') === null]")
    ok('memo text, walking time and the closed cards survive closing the page', kept == ['識別證', after[2], True], str(kept))
    pg.tap('#memoClear'); pg.wait_for_timeout(200); ok('the clear button empties the memo', pg.evaluate("document.getElementById('memoText').value") == '' and pg.evaluate("localStorage.xw_memo") == '""')
    # --- pull to refresh
    pg.evaluate('window.__mark = 1'); fire = lambda t, x, y: pg.evaluate(f"({FIRE})('{t}',{x},{'null' if y is None else y})")
    fire('touchstart', 200, 300); fire('touchmove', 200, 340); fire('touchend', 200, None); pg.wait_for_timeout(500)
    ok('a short pull does not reload', pg.evaluate('window.__mark === 1') and pg.evaluate("document.querySelector('main').style.transform") == '')
    fire('touchstart', 200, 300); fire('touchmove', 200, 330); fire('touchmove', 200, 560); fire('touchend', 200, None); pg.wait_for_timeout(1200)
    ok('a long pull reloads the page', pg.evaluate('window.__mark !== 1'))
    ctx.close(); wk.close()

    # --- drag to reorder (mouse) and offline start (service worker) in Chromium
    cr = p.chromium.launch(); ctx, pg, errs = new_page(cr)
    start = pg.evaluate(NAMES)
    pg.click('.x.open .xhead'); pg.click('#more > summary'); pg.wait_for_timeout(200); pg.click('#adv > summary'); pg.wait_for_timeout(250)
    def drag(i, j):
        a = pg.locator('.orow .grip').nth(i).bounding_box(); t = pg.locator('.orow').nth(j).bounding_box()
        y0 = a['y'] + a['height'] / 2; y1 = t['y'] + t['height'] * (0.8 if j > i else 0.2)
        pg.mouse.move(a['x'] + 22, y0); pg.mouse.down()
        for k in range(1, 9): pg.mouse.move(a['x'] + 22, y0 + (y1 - y0) * k / 8); pg.wait_for_timeout(30)
        pg.mouse.up(); pg.wait_for_timeout(300)
    drag(0, 2); ok('dragging the first crossing to the bottom reorders the cards', pg.evaluate(NAMES) == start[1:] + start[:1], str(pg.evaluate(NAMES)))
    drag(2, 0); ok('dragging it back up restores the order', pg.evaluate(NAMES) == start)
    drag(0, 1); pg.goto('about:blank'); pg.goto(URL); pg.wait_for_timeout(1000)
    ok('the chosen order is remembered', pg.evaluate(NAMES) == [start[1], start[0], start[2]])
    ok('the offline copy is installed', pg.evaluate('navigator.serviceWorker.ready.then(r => !!r.active)'))
    ctx.set_offline(True); pg.reload(); pg.wait_for_timeout(1500)
    ok('the page opens and counts down without a network', pg.evaluate("document.querySelectorAll('.x').length") == 3 and pg.evaluate("document.querySelector('.xsum b').textContent") != '')
    ctx.close(); cr.close()
print(f'\n{n} checks passed'); srv.shutdown()
