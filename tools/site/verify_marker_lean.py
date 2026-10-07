#!/usr/bin/env python3
"""Check the public highlighter's bounded lean and rectangular resting shape."""
from __future__ import annotations
import argparse, datetime, json, os, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

ROUTES = ('/', '/en/', '/projects/ko/', '/projects/en/')
EPOCH = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', default='https://kjw988.github.io')
    ap.add_argument('--output', type=Path, default=Path('live-check-results'))
    args = ap.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    base = args.base.rstrip('/'); checks = []; errors = []
    with sync_playwright() as pw:
        opts = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            opts['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = pw.chromium.launch(**opts)
        ready = browser.new_page()
        for attempt in range(18):
            ready.goto(base + '/projects/ko/', wait_until='load')
            if ready.locator('[data-lean-version="spring-lean-v1"]').count() == 1:
                break
            if attempt == 17:
                raise AssertionError('The leaning marker build is not public yet')
            time.sleep(10)
        ready.close()
        for width in (1440, 768, 390, 320):
            for route in ROUTES:
                ctx = browser.new_context(viewport={'width': width, 'height': 960}, reduced_motion='no-preference')
                p = ctx.new_page(); p.on('pageerror', lambda e: errors.append(str(e)))
                try:
                    assert p.goto(base + route, wait_until='load').status == 200
                    p.evaluate('document.fonts.ready')
                    pair = p.locator('.moves-pair'); mark = p.locator('.moves-mark'); us = p.locator('.moves-us')
                    assert pair.get_attribute('data-lean-version') == 'spring-lean-v1'
                    m0 = mark.bounding_box(); u0 = us.bounding_box(); outer = pair.bounding_box()
                    color = mark.evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')
                    assert color == 'rgb(240, 207, 85)'
                    p.clock.install(time=EPOCH); p.clock.pause_at(EPOCH + datetime.timedelta(seconds=1))
                    p.evaluate('''()=>{
                      window.leanTrace=[];
                      const pair=document.querySelector('.moves-pair'),m=pair.querySelector('.moves-mark');
                      function sample(){
                        const css=getComputedStyle(m,'::before');
                        leanTrace.push({
                          right:parseFloat(pair.style.getPropertyValue('--marker-lean-right'))||0,
                          left:parseFloat(pair.style.getPropertyValue('--marker-lean-left'))||0,
                          height:parseFloat(css.height),clip:css.clipPath,
                          overflow:document.documentElement.scrollWidth>innerWidth+1});
                        if(leanTrace.length<160)requestAnimationFrame(sample);
                      }requestAnimationFrame(sample);
                    }''')
                    mark.dispatch_event('pointerenter'); p.clock.run_for(2700)
                    trace = p.evaluate('leanTrace'); assert len(trace) > 100
                    assert max(t['right'] for t in trace) > .5
                    assert max(t['left'] for t in trace) > .5
                    assert len({t['clip'] for t in trace}) > 8
                    assert all(not t['overflow'] and max(t['right'], t['left']) < t['height'] * .20 for t in trace)
                    assert mark.bounding_box() == m0 and pair.bounding_box() == outer
                    assert abs(us.bounding_box()['x'] - u0['x']) < .1
                    assert mark.evaluate('(e)=>getComputedStyle(e).fontStyle') == 'normal'
                    assert not pair.evaluate('(e)=>e.classList.contains("is-moving")')
                    assert pair.evaluate("e=>!e.style.getPropertyValue('--marker-lean-right')&&!e.style.getPropertyValue('--marker-lean-left')")
                    checks.append({'route': route, 'width': width, 'lean_both_directions': True, 'rectangular_rest': True, 'upright_text': True})
                except Exception:
                    errors.append({'route': route, 'width': width, 'error': traceback.format_exc()})
                finally:
                    ctx.close()
        for route in ROUTES:
            ctx = browser.new_context(reduced_motion='reduce')
            p = ctx.new_page()
            try:
                assert p.goto(base + route).status == 200
                p.locator('.moves-mark').dispatch_event('click'); p.wait_for_timeout(80)
                assert p.locator('.moves-mark').evaluate('(e)=>getComputedStyle(e,"::before").clipPath') == 'none'
                assert not p.locator('.moves-pair').evaluate('(e)=>e.classList.contains("is-moving")')
            except Exception:
                errors.append({'reduced_motion': route, 'error': traceback.format_exc()})
            finally:
                ctx.close()
        browser.close()
    report = {'mode': 'live HTTPS + Chromium', 'checks': checks, 'errors': errors}
    (args.output / 'marker-lean-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Marker lean: {len(checks)}/16 route/width checks; errors={len(errors)}')
    if errors or len(checks) != 16:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
