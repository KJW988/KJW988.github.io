#!/usr/bin/env python3
"""공개 Pages를 실제 Chromium으로 검사합니다. 사이트 빌드에는 필요하지 않습니다."""
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from publish import BASE, FIGURES, PAPER_IDS, paper_url
from content import PAPERS

OUT = Path('live-check-results')

def get(url):
    with urlopen(url, timeout=30) as response:
        assert response.status == 200, (url, response.status)
        return response.read()

def main():
    OUT.mkdir(exist_ok=True)
    errors, checked, http, navigation = [], [], [], []
    for attempt in range(8):
        try:
            page = get(BASE + '/endcache/ko/').decode()
            assert paper_url('endcache') in page
            assert 'class="method-copy"' in page and 'class="blog-back"' in page
            break
        except Exception:
            if attempt == 7: raise
            time.sleep(10)
    for slug, expected in FIGURES.items():
        url = f'{BASE}/assets/{slug}.webp'
        raw = get(url)
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected
        http.append({'url': url, 'status': 200, 'figure_integrity': True})
    for route in ('https://kjw988.github.io/', 'https://kjw988.github.io/research/'):
        get(route)
        http.append({'url': route, 'status': 200})
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(reduced_motion='reduce', permissions=['clipboard-read', 'clipboard-write'])
        for width in (1440, 390, 320):
            for lang in ('ko', 'en'):
                for slug in ('', *PAPER_IDS):
                    route = f'{BASE}/{slug + "/" if slug else ""}{lang}/'
                    name = f'{slug or "index"}-{lang}-{width}'
                    page = context.new_page()
                    page.set_viewport_size({'width': width, 'height': 960 if width == 1440 else 844})
                    page.set_default_timeout(8000)
                    page.on('pageerror', lambda e, n=name: errors.append(n + ': ' + str(e)))
                    try:
                        response = page.goto(route, wait_until='load')
                        assert response.status == 200
                        assert page.locator('html').get_attribute('lang') == lang
                        assert page.locator('h1').count() == 1
                        assert page.locator('iframe').count() == 0
                        assert page.locator('.blog-back').is_visible()
                        assert page.locator('.blog-back').get_attribute('href') == 'https://kjw988.github.io/' 
                        page.evaluate("async () => {const a=Array.from(document.querySelectorAll('img[src]')); a.forEach(i=>i.loading='eager'); await Promise.all(a.map(i=>i.decode()));}")
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'horizontal overflow'
                        if lang == 'ko' and (width == 1440 and slug in ('', 'endcache') or width == 390 and slug == 'lift3d-film'):
                            page.screenshot(path=str(OUT / f'{name}.png'))
                        if slug:
                            assert page.locator('.paper-link').get_attribute('href') == paper_url(slug)
                            assert page.locator('.step, .walkthrough, #step-count').count() == 0
                            assert page.locator('#method button').count() == 0
                            paragraphs = page.locator('#method .method-copy p')
                            source = next(p for p in PAPERS if p['slug'] == slug)
                            assert paragraphs.all_text_contents() == [body[lang] for _, body in source['sections']]
                            page.locator('.zoom').click()
                            assert page.locator('#figure-dialog').evaluate('(d)=>d.open')
                            page.locator('#close-dialog').click()
                            assert not page.locator('#figure-dialog').evaluate('(d)=>d.open')
                            if slug in ('endcache', 'velocity-reuse'):
                                page.locator('#cache-k').fill('0')
                                page.locator('#cache-k').dispatch_event('input')
                                assert page.locator('#cache-k-output').inner_text() == 'k = 1'
                                page.locator('#cache-model').select_option(index=1)
                                assert page.locator('#cache-values').inner_text().strip()
                            elif slug == 'lift3d-film':
                                page.locator('#film-gamma').fill('2')
                                page.locator('#film-gamma').dispatch_event('input')
                                page.locator('#film-beta').fill('0.5')
                                page.locator('#film-beta').dispatch_event('input')
                                assert '2.10' in page.locator('#film-vector').inner_text()
                                page.locator('#film-task').select_option(index=0)
                                assert page.locator('.missing').count() == 1
                            else:
                                page.locator('#study-select').select_option(index=1)
                                page.locator('#metric-select').select_option(index=0)
                                assert page.locator('#study-plot').inner_text().strip()
                            page.locator('#copy').click()
                            page.wait_for_function("document.getElementById('copy-status').textContent.trim().length > 0")
                            if lang == 'ko' and width == 390:
                                page.locator('.section-nav a[href="#results"]').click()
                                page.locator('.language[hreflang="en"]').click()
                                page.wait_for_url(f'{BASE}/{slug}/en/index.html#results')
                                assert page.locator('html').get_attribute('lang') == 'en'
                                page.locator('.language[hreflang="ko"]').click()
                                page.wait_for_url(f'{BASE}/{slug}/ko/index.html#results')
                        else:
                            page.locator('.filter[data-filter="control"]').click()
                            assert page.locator('.card:visible').count() == 2
                            page.locator('.filter[data-filter="all"]').click()
                            page.locator('#search').fill('endcache')
                            assert page.locator('.card:visible').count() == 1
                            page.locator('.card-link:visible').click()
                            page.wait_for_url(f'{BASE}/endcache/{lang}/index.html')
                        checked.append({'url': route, 'width': width, 'status': 200})
                        print('PASS', name, route, flush=True)
                    except Exception as e:
                        errors.append(name + ': ' + traceback.format_exc())
                        print('FAIL', name, traceback.format_exc(), flush=True)
                    finally:
                        page.close()
        # Real navigation: sidebar -> gallery -> blog, and legacy URL without a detour.
        page = context.new_page()
        page.set_viewport_size({'width': 1440, 'height': 960})
        page.set_default_timeout(10000)
        try:
            page.goto('https://kjw988.github.io/', wait_until='load')
            sidebar = page.locator('#sidebar a.nav-link[href="/projects/ko/"]')
            assert sidebar.count() == 1, 'research sidebar must point directly to the gallery'
            sidebar.click()
            page.wait_for_url(BASE + '/ko/')
            assert page.locator('.card').count() == 6
            page.locator('.blog-back').click()
            page.wait_for_url('https://kjw988.github.io/')
            for lang in ('ko', 'en'):
                page.evaluate('(l) => localStorage.setItem("research-language", l)', lang)
                page.goto('https://kjw988.github.io/research/?from=legacy#main', wait_until='load')
                page.wait_for_url(BASE + '/' + lang + '/?from=legacy#main')
                assert page.locator('.card').count() == 6
                navigation.append({'legacy_language': lang, 'destination': page.url})
            page.locator('.blog-back').click()
            page.wait_for_url('https://kjw988.github.io/')
            navigation.append({'sidebar_direct': True, 'return_to_blog': True})
        except Exception:
            errors.append('navigation: ' + traceback.format_exc())
        finally:
            page.close()
        nojs = browser.new_context(java_script_enabled=False)
        page = nojs.new_page()
        try:
            page.goto('https://kjw988.github.io/research/', wait_until='load')
            page.wait_for_url(BASE + '/ko/')
            assert page.locator('.card').count() == 6
            navigation.append({'no_javascript_redirect': True})
        except Exception:
            errors.append('no-js redirect: ' + traceback.format_exc())
        finally:
            nojs.close()
        browser.close()
    report = {'mode': 'live public HTTPS + Chromium', 'checked': checked, 'http': http, 'errors': errors,
              'navigation': navigation, 'passed_combinations': len(checked), 'language_round_trips': 6 if not errors else None,
              'drive_permission_check': 'not performed; original URLs linked without permission changes'}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = f'공개 사이트 브라우저 검사: {len(checked)}/42 조합 통과, 오류 {len(errors)}개.\n'
    print(summary + json.dumps(report, ensure_ascii=False), flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f: f.write(summary)
    if errors: raise SystemExit(1)

if __name__ == '__main__': main()
