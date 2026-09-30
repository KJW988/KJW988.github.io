#!/usr/bin/env python3
"""Check actual published seminar pages, with expected counts from the uploaded bundle."""
import argparse, json, os, re, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
from install import selection

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='https://kjw988.github.io')
    parser.add_argument('--output',type=Path,default=Path('seminar-check-results'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mode,meta,missing=selection();base=args.base.rstrip('/')
    if mode=='waiting':
        print('No rendered bundle; public seminar checks are NOT performed.');return
    errors=[];checks=[];network=[];video_checks=[];navigation=[]
    with sync_playwright() as p:
        opts={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=p.chromium.launch(**opts)
        page=browser.new_page();page.set_default_timeout(20000)
        target=base+'/seminars/?v='+meta['bundle_sha256'][:12]
        for attempt in range(12):
            response=page.goto(target,wait_until='load')
            count=page.evaluate('window.SEMINAR_DECKS?.length')
            if response.status==200 and count==meta['deck_count']:break
            if attempt==11:raise AssertionError('Expected seminar version is not published')
            time.sleep(10)
        decks=page.evaluate('window.SEMINAR_DECKS')
        assert sum(len(d['slides']) for d in decks)==meta['source_slide_count']
        assert sum(len(s['frames']) for d in decks for s in d['slides'])==meta['rendered_state_count']
        page.close()
        # New contexts bound decoded-image memory when scanning hundreds of SVGs rapidly.
        for width in (1440,390,320):
            for deck in decks:
                context=browser.new_context(viewport={'width':width,'height':1000 if width==1440 else 844},reduced_motion='reduce')
                page=context.new_page();page.set_default_timeout(20000)
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:network.append(r.url))
                try:
                    response=page.goto(target,wait_until='load');assert response.status==200
                    assert page.locator('html').get_attribute('lang')=='ko'
                    assert page.locator('iframe,[data-lang],a[download]').count()==0
                    for slide in deck['slides']:
                        for step,frame in enumerate(slide['frames']):
                            page.evaluate('(h)=>location.hash=h',f"#{deck['id']}/{slide['original']}/{step}")
                            page.wait_for_function("f=>{const i=document.getElementById('slide-image');return i.getAttribute('src')===f&&i.complete&&i.naturalWidth>0}",arg=frame)
                            box=page.locator('.stage').bounding_box();ratio=slide['dimensions']['width']/slide['dimensions']['height']
                            assert abs(box['width']-box['height']*ratio)<1.1
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            assert not page.locator('#load-error').is_visible()
                            checks.append({'width':width,'deck':deck['id'],'slide':slide['original'],'step':step})
                    assert page.locator('#next').is_disabled()
                    page.locator('#thumbnails-toggle').click();page.locator('#thumbnails .thumb').last.click()
                    assert page.locator('#original-count').inner_text()==f"원본 {deck['slides'][-1]['original']} / {deck['originalCount']}"
                    page.locator('#thumbnails-toggle').click()
                    if deck['id']=='bac':
                        page.evaluate("location.hash='#bac/3/0'");page.wait_for_function("document.getElementById('build-count').textContent==='단계 1 / 3'")
                        page.locator('#next').click();assert page.locator('#build-count').inner_text()=='단계 2 / 3'
                        page.locator('#prev').click();assert page.locator('#build-count').inner_text()=='단계 1 / 3'
                        page.locator('#zoom').click();assert page.locator('#zoom-dialog').evaluate('(e)=>e.open');page.locator('#zoom-close').click()
                        page.locator('#fullscreen').click();page.wait_for_function("document.fullscreenElement||document.getElementById('player').classList.contains('presentation-mode')");page.locator('#fullscreen').click()
                        if width in (1440,390):page.screenshot(path=str(args.output/f'viewer-{width}.png'),full_page=True)
                    if width==1440:
                        seen=set()
                        for slide in deck['slides']:
                            for media in slide.get('media',[]):
                                if media['src'] in seen:continue
                                seen.add(media['src']);step=media.get('steps',[0])[0]
                                page.evaluate('(h)=>location.hash=h',f"#{deck['id']}/{slide['original']}/{step}")
                                page.wait_for_function("src=>[...document.querySelectorAll('#media-layer video')].some(v=>v.getAttribute('src')===src&&v.readyState>=2)",arg=media['src'])
                                page.locator('#motion').click();page.wait_for_function("[...document.querySelectorAll('#media-layer video')].every(v=>!v.paused&&v.currentTime>0)")
                                page.locator('#motion').click();assert page.locator('#media-layer video').first.evaluate('(v)=>v.paused')
                                video_checks.append({'deck':deck['id'],'slide':slide['original'],'play_pause':True})
                        if deck['id']=='vla-cache':page.screenshot(path=str(args.output/'pdf-native-ratio.png'),full_page=True)
                    navigation.append({'deck':deck['id'],'width':width,'last_slide':True})
                    print('PASS',deck['id'],width,len(deck['slides']),flush=True)
                except Exception:errors.append(deck['id']+': '+traceback.format_exc())
                finally:context.close()
        page=browser.new_page()
        try:
            for route in ('/','/en/','/blog/'):
                page.goto(base+route,wait_until='load')
                assert page.locator('a[href="/seminars/"]').count()>=1,route
            navigation.append({'about_and_blog_links':True})
        except Exception:errors.append('navigation: '+traceback.format_exc())
        browser.close()
    prohibited=[u for u in network if re.search(r'\.(pptx?|pdf|zip|ttf|otf|woff2?)(?:[?#]|$)',u,re.I)]
    if prohibited:errors.append('Source-document/font requests: '+repr(prohibited))
    expected_states=meta['rendered_state_count']*3
    if len(checks)!=expected_states:errors.append(f'Expected {expected_states} state/viewport checks, got {len(checks)}')
    report={'mode':'live HTTPS + Chromium','bundle_mode':mode,'deck_count':len(decks),'source_slide_count':meta['source_slide_count'],
            'rendered_state_count':meta['rendered_state_count'],'passed_states':len(checks),'expected_states':expected_states,
            'checks':checks,'errors':errors,'video_checks':video_checks,'navigation':navigation,
            'original_document_requests':len(prohibited),'missing_full_parts':missing}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(f'Seminars {mode}: {len(checks)}/{expected_states} state/viewport checks, errors={len(errors)}')
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
