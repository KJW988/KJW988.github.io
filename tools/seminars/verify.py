#!/usr/bin/env python3
"""Check published rendered slides; sample coverage is never reported as full coverage."""
import argparse, json, os, re, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
from install import selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://kjw988.github.io')
    parser.add_argument('--output', type=Path, default=Path('seminar-check-results'))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    mode, meta, missing = selection(); base = args.base.rstrip('/')
    if mode == 'waiting':
        raise SystemExit('No rendered bundle; public seminar checks were NOT performed.')
    checks, errors, videos, network, navigation = [], [], [], [], []
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = pw.chromium.launch(**options)
        page = browser.new_page(); page.set_default_timeout(20000)
        target = base + '/seminars/?v=' + meta['bundle_sha256'][:12]
        for attempt in range(12):
            response = page.goto(target, wait_until='load')
            if response.status == 200 and page.evaluate('window.SEMINAR_DECKS?.length') == meta['deck_count'] and page.locator('[data-page-numbering="ppt-cover-zero-v1"]').count():
                break
            if attempt == 11: raise AssertionError('Expected seminar bundle and numbering are not published')
            time.sleep(10)
        decks = page.evaluate('window.SEMINAR_DECKS')
        assert sum(len(d['slides']) for d in decks) == meta['source_slide_count']
        assert sum(len(s['frames']) for d in decks for s in d['slides']) == meta['rendered_state_count']
        page.close()
        for width in (1440, 390, 320):
            for deck in decks:
                offset = 0 if re.search(r'\bPDF\b', deck.get('description', ''), re.I) else 1
                last_page = deck['originalCount'] - offset
                ctx = browser.new_context(viewport={'width': width, 'height': 1000 if width == 1440 else 844}, reduced_motion='reduce')
                page = ctx.new_page(); page.set_default_timeout(20000)
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('request', lambda r: network.append(r.url))
                try:
                    assert page.goto(target, wait_until='load').status == 200
                    assert page.locator('html').get_attribute('lang') == 'ko'
                    assert page.locator('iframe,[data-lang],a[download]').count() == 0
                    assert page.locator('#original-count,#build-count,#sample-count,.sample-info,#scope-copy,.intro .sample-note').count() == 0
                    assert '10개 발표자료 · 405장' not in page.locator('body').inner_text()
                    for slide in deck['slides']:
                        for step, frame in enumerate(slide['frames']):
                            page.evaluate('(h)=>location.hash=h', f"#{deck['id']}/{slide['original']}/{step}")
                            page.wait_for_function("f=>{const i=document.getElementById('slide-image');return i.getAttribute('src')===f&&i.complete&&i.naturalWidth>0}", arg=frame)
                            assert page.locator('#page-count').inner_text() == f"{slide['original'] - offset} / {last_page}"
                            box = page.locator('.stage').bounding_box(); ratio = slide['dimensions']['width'] / slide['dimensions']['height']
                            assert abs(box['width'] - box['height'] * ratio) < 1.1
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            assert not page.locator('#load-error').is_visible()
                            if width == 1440 and deck['id'] in ('ddt', 'vla-cache') and slide['original'] in (1, 2) and step == 0:
                                page.locator('#player').screenshot(path=str(args.output/f"{deck['id']}-page-{slide['original'] - offset}.png"))
                            checks.append({'width': width, 'deck': deck['id'], 'slide': slide['original'], 'display_page': slide['original'] - offset, 'step': step})
                    assert page.locator('#next').is_disabled()
                    assert page.locator('#thumbnails .thumb').count() == len(deck['slides'])
                    assert page.locator('#thumbnails .thumb > span').all_text_contents() == [str(s['original'] - offset) for s in deck['slides']]
                    page.locator('#thumbnails-toggle').click(); page.locator('#thumbnails .thumb').last.click()
                    assert page.locator('#page-count').inner_text() == f"{deck['slides'][-1]['original'] - offset} / {last_page}"
                    page.locator('#thumbnails-toggle').click()
                    if deck['id'] == 'bac':
                        page.evaluate("location.hash='#bac/3/0'")
                        page.wait_for_function("document.getElementById('page-count').textContent==='2 / 45' && location.hash==='#bac/3/0'")
                        progress=page.locator('#progress > span').get_attribute('style')
                        page.locator('#next').click(); assert page.evaluate('location.hash') == '#bac/3/1'
                        assert page.locator('#page-count').inner_text() == '2 / 45'
                        assert page.locator('#progress > span').get_attribute('style') == progress
                        page.locator('#prev').click(); assert page.evaluate('location.hash') == '#bac/3/0'
                        assert page.locator('#page-count').inner_text() == '2 / 45'
                        page.locator('#zoom').click(); assert page.locator('#zoom-dialog').evaluate('(e)=>e.open'); page.locator('#zoom-close').click()
                        page.locator('#fullscreen').click()
                        page.wait_for_function("document.fullscreenElement||document.getElementById('player').classList.contains('presentation-mode')")
                        page.locator('#fullscreen').click()
                        if width in (1440, 390): page.screenshot(path=str(args.output/f'viewer-{width}.png'), full_page=True)
                    if width == 1440:
                        seen = set()
                        for slide in deck['slides']:
                            for media in slide.get('media', []):
                                if media['src'] in seen: continue
                                seen.add(media['src']); step = media.get('steps', [0])[0]
                                page.evaluate('(h)=>location.hash=h', f"#{deck['id']}/{slide['original']}/{step}")
                                page.wait_for_function("src=>[...document.querySelectorAll('#media-layer video')].some(v=>v.getAttribute('src')===src&&v.readyState>=2)", arg=media['src'])
                                page.locator('#motion').click()
                                page.wait_for_function("[...document.querySelectorAll('#media-layer video')].every(v=>!v.paused&&v.currentTime>0)")
                                page.locator('#motion').click(); assert page.locator('#media-layer video').first.evaluate('(v)=>v.paused')
                                videos.append({'deck': deck['id'], 'slide': slide['original'], 'play_pause': True})
                        if deck['id'] == 'vla-cache': page.screenshot(path=str(args.output/'pdf-native-ratio.png'), full_page=True)
                    navigation.append({'deck': deck['id'], 'width': width, 'last_slide': True, 'numbering_offset': offset})
                except Exception: errors.append(deck['id'] + ': ' + traceback.format_exc())
                finally: ctx.close()
        page = browser.new_page()
        try:
            for route in ('/', '/en/', '/projects/ko/', '/projects/en/'):
                assert page.goto(base+route, wait_until='load').status == 200
                assert page.locator('.sitewide-header a[href="/seminars/"]').count() == 1
            assert page.request.get(base+'/blog/').status == 404
            navigation.append({'home_publication_seminar_links': True, 'retired_blog_404': True})
        except Exception: errors.append('navigation: ' + traceback.format_exc())
        browser.close()
    prohibited = [u for u in network if re.search(r'\.(pptx?|pdf|zip|ttf|otf|woff2?)(?:[?#]|$)', u, re.I)]
    if prohibited: errors.append('Source-document/font requests: ' + repr(prohibited))
    expected = meta['rendered_state_count'] * 3
    if len(checks) != expected: errors.append(f'Expected {expected} state/viewport checks, got {len(checks)}')
    report = {'mode': 'live HTTPS + Chromium', 'bundle_mode': mode, 'complete': mode == 'full', 'deck_count': len(decks),
              'source_slide_count': meta['source_slide_count'], 'rendered_state_count': meta['rendered_state_count'],
              'passed_states': len(checks), 'expected_states': expected, 'checks': checks, 'errors': errors,
              'video_checks': videos, 'navigation': navigation, 'original_document_requests': len(prohibited), 'missing_full_parts': missing}
    (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Seminars {mode}: {len(checks)}/{expected} state/viewport checks, errors={len(errors)}')
    if errors: raise SystemExit(1)

if __name__ == '__main__': main()
