#!/usr/bin/env python3
"""Check rendered research questions, tags, line breaks and unchanged paper content."""
import argparse, json, os, re, sys, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
from presentation import COPY
from headings import INTRO_KO, INTRO_EN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://kjw988.github.io')
    parser.add_argument('--output', type=Path, default=Path('live-check-results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.base.rstrip('/')
    checks, errors, js_errors = [], [], []
    with sync_playwright() as pw:
        opts = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            opts['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = pw.chromium.launch(**opts)
        context = browser.new_context(reduced_motion='reduce')
        ready = context.new_page()
        for attempt in range(12):
            ready.goto(base + '/projects/ko/', wait_until='load')
            if ready.locator('.card .paper-summary').count() == 6:
                break
            if attempt == 11:
                raise AssertionError('Updated publication summaries are not deployed')
            time.sleep(10)
        ready.close()
        for lang in ('ko', 'en'):
            for width in (1440, 768, 390, 320):
                for slug in ('', *COPY):
                    page = context.new_page()
                    page.set_viewport_size({'width': width, 'height': 960})
                    page.set_default_timeout(15000)
                    page.on('pageerror', lambda e: js_errors.append(str(e)))
                    route = f'/projects/{slug + "/" if slug else ""}{lang}/'
                    try:
                        assert page.goto(base + route, wait_until='load').status == 200
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        if not slug:
                            assert page.locator('.index-hero > .eyebrow').inner_text() == '2024-2026'
                            intro = page.locator('.index-intro')
                            assert intro.inner_text() == (INTRO_KO if lang == 'ko' else INTRO_EN)
                            assert intro.evaluate('(e)=>getComputedStyle(e).whiteSpace') == 'pre-line'
                            cards = page.locator('.card')
                            assert cards.count() == 6
                            for i, (key, item) in enumerate(COPY.items()):
                                card = cards.nth(i)
                                assert card.locator('.paper-alias').inner_text() == item['name']
                                assert card.locator('.summary-question').inner_text() == item['question'][lang]
                                assert card.locator('.tags span').all_text_contents() == item['tags']
                                assert card.locator('.summary-points li').all_text_contents() == item.get('points', {}).get(lang, [])
                                if item.get('detail'):
                                    assert card.locator('.summary-detail').inner_text() == item['detail'][lang]
                            for query, count in [('Training-free', 2), ('Adversarial Attack', 1), ('VLN', 1), ('FiLM', 1), ('NaVILA', 0), ('Traffic', 1)]:
                                page.locator('#search').fill(query)
                                assert page.locator('.card:visible').count() == count, query
                            page.locator('#search').fill('')
                            page.locator('[data-filter="efficiency"]').click()
                            assert page.locator('.card:visible').count() == 2
                            page.locator('[data-filter="all"]').click()
                            if width in (1440, 390):
                                page.evaluate("async()=>{await Promise.all([...document.querySelectorAll('img')].map(i=>{i.loading='eager';return i.decode()}))}")
                                page.screenshot(path=str(args.output/f'editorial-index-{lang}-{width}.png'), full_page=True)
                        else:
                            item = COPY[slug]
                            assert page.locator('main > .paper-summary .lead').inner_text() == item['question'][lang]
                            assert page.locator('.paper-tags span').all_text_contents() == item['tags']
                            assert page.locator('main > .paper-summary .summary-points li').all_text_contents() == item.get('points', {}).get(lang, [])
                            data = page.locator('#paper-data').text_content()
                            data = json.loads(data)
                            assert data['name'] == item['name'] and data['tags'] == item['tags']
                            assert page.locator('#method .method-copy p').all_text_contents() == [body[lang] for _, body in data['sections']]
                            assert page.locator('#method button,.paper-summary button').count() == 0
                            assert page.locator('.paper-link').count() == 1
                            if slug == 'navila-patch':
                                assert 'Adversarial Patch /' in page.locator('.hero > .eyebrow').inner_text()
                                assert 'VLN Patch Study' not in page.locator('body').inner_text()
                            if width in (1440,390) and lang == 'ko' and slug in ('endcache','star','navila-patch'):
                                page.locator('main > .paper-summary').screenshot(path=str(args.output/f'editorial-{slug}-{width}.png'))
                        checks.append({'route':route,'width':width,'passed':True})
                    except Exception:
                        errors.append({'route':route,'width':width,'error':traceback.format_exc()})
                    finally:
                        page.close()
        nojs = browser.new_context(java_script_enabled=False)
        page = nojs.new_page()
        for lang in ('ko','en'):
            page.goto(base + f'/projects/{lang}/')
            assert page.locator('.card .paper-summary').count() == 6
            assert page.locator('.summary-points li').count() == 3
        nojs.close()
        browser.close()
    report = {'mode':'HTTPS browser' if base.startswith('https:') else 'local HTTP browser', 'checks':checks, 'passed_combinations':len(checks), 'expected_combinations':56, 'errors':errors, 'javascript_errors':js_errors}
    (args.output/'editorial-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    if errors or js_errors or len(checks) != 56:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
