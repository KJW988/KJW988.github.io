#!/usr/bin/env python3
"""Verify replacement overviews, rendered aspect ratio, cards and resolved zoom URLs."""
from pathlib import Path
import hashlib, json, time, traceback
from playwright.sync_api import sync_playwright

BASE = 'https://kjw988.github.io'
VERSION = 'author-overviews-20261002-v2'
EXPECTED = {'lift3d-film': [2048, 1008], 'act-cbam': [1915, 665]}
SOURCES = {'lift3d-film': 'f8db588283c16e74002517257a78d2feb4139bb7907ea518064f650aa1e6159d',
           'act-cbam': '4bd7be0fc0550161eebcfad8dfe6052fd6ce40e37255dac68cb6cc287b327d9e'}

def main():
    output = Path('live-check-results'); output.mkdir(exist_ok=True)
    report = {'mode': 'live HTTPS + Chromium', 'media': [], 'details': [], 'overviews': [], 'errors': []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(reduced_motion='reduce', service_workers='block')
            for attempt in range(12):
                response = ctx.request.get(BASE + '/projects/author-figures.json')
                if response.status == 200 and response.json().get('version') == VERSION:
                    status = response.json(); break
                if attempt == 11: raise AssertionError('New figure layout is not deployed')
                time.sleep(10)
            assert set(status['figures']) == set(EXPECTED)
            for slug, spec in status['figures'].items():
                assert spec['source_sha256'] == SOURCES[slug] and spec['dimensions'] == EXPECTED[slug]
                response = ctx.request.get(BASE + '/projects/assets/' + spec['file'])
                assert response.status == 200 and hashlib.sha256(response.body()).hexdigest() == spec['sha256']
                report['media'].append({'slug': slug, 'dimensions': spec['dimensions'], 'file': spec['file'], 'sha256': spec['sha256']})
            def validate_image(image, slug):
                image.scroll_into_view_if_needed(); image.evaluate('(e)=>e.decode()')
                assert image.evaluate('(e)=>[e.naturalWidth,e.naturalHeight]') == EXPECTED[slug]
                assert image.evaluate('(e)=>e.src').endswith('/' + status['figures'][slug]['file'])
            for width in (1440, 768, 390, 320):
                for lang in ('ko', 'en'):
                    for slug, spec in status['figures'].items():
                        route = f'/projects/{slug}/{lang}/'; p = ctx.new_page()
                        p.set_viewport_size({'width': width, 'height': 960})
                        p.on('pageerror', lambda e: report['errors'].append(str(e)))
                        try:
                            assert p.goto(BASE + route, wait_until='load').status == 200
                            figure = p.locator('.paper-figure .zoom img')
                            validate_image(figure, slug)
                            rendered_ratio = figure.evaluate('(e)=>{const r=e.getBoundingClientRect();return r.width/r.height}')
                            assert abs(rendered_ratio - EXPECTED[slug][0]/EXPECTED[slug][1]) < .02
                            assert p.locator('meta[property="og:image"]').get_attribute('content').endswith('/' + spec['file'])
                            assert p.locator('#results table').count() == 1
                            assert p.locator('#explorer,#limits,#citation,a[download]').count() == 0
                            assert p.locator('main > section').last.get_attribute('id') == 'related'
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            p.locator('.zoom').click()
                            assert p.locator('#figure-dialog').evaluate('(e)=>e.open')
                            zoom = p.locator('#figure-dialog img'); zoom.evaluate('(e)=>e.decode()')
                            assert zoom.evaluate('(e)=>[e.naturalWidth,e.naturalHeight]') == EXPECTED[slug]
                            # Zoom assigns img.src, which resolves relative paths to absolute URLs.
                            # Compare resolved URLs rather than unlike raw src attributes.
                            assert zoom.evaluate('(e)=>e.src') == figure.evaluate('(e)=>e.src')
                            p.locator('#close-dialog').click()
                            assert not p.locator('#figure-dialog').evaluate('(e)=>e.open')
                            if width in (1440, 390) and lang == 'ko':
                                p.locator('.paper-figure').screenshot(path=str(output / f'{slug}-new-figure-{width}.png'))
                            report['details'].append({'route': route, 'width': width, 'full_resolution_and_zoom': True, 'original_aspect_ratio': True})
                        except Exception:
                            report['errors'].append({'route': route, 'width': width, 'error': traceback.format_exc()})
                        finally: p.close()
                    for route, home in [(f'/projects/{lang}/', False), ('/' if lang == 'ko' else '/en/', True)]:
                        p = ctx.new_page(); p.set_viewport_size({'width': width, 'height': 960})
                        try:
                            assert p.goto(BASE + route, wait_until='load').status == 200
                            for slug in (('lift3d-film',) if home else tuple(EXPECTED)):
                                image = p.locator(f'.research-image[href="/projects/{slug}/{lang}/"] img') if home else p.locator(f'.card-cover[href="../{slug}/{lang}/index.html"] img')
                                validate_image(image, slug)
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            assert p.locator('.research-card' if home else '.card').count() == (3 if home else 6)
                            report['overviews'].append({'route': route, 'width': width, 'thumbnails_updated': True})
                        except Exception:
                            report['errors'].append({'route': route, 'width': width, 'error': traceback.format_exc()})
                        finally: p.close()
            ctx.close(); browser.close()
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        (output / 'author-figures-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in report.items()}, ensure_ascii=False))
    if report['errors'] or len(report['details']) != 16 or len(report['overviews']) != 16:
        raise SystemExit(1)

if __name__ == '__main__': main()
