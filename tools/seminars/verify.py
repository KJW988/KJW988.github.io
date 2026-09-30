#!/usr/bin/env python3
"""Verify the published Korean, rendered-only seminar viewer in Chromium."""
import argparse
import json
import os
from pathlib import Path
import time
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='https://kjw988.github.io')
    parser.add_argument('--output',type=Path,default=Path('seminar-check-results'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    base=args.base.rstrip('/');errors=[];checks=[];network=[]
    with sync_playwright() as p:
        options={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=p.chromium.launch(**options)
        context=browser.new_context(reduced_motion='reduce')
        page=context.new_page();page.set_default_timeout(12000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:network.append(r.url))
        for attempt in range(10):
            response=page.goto(base+'/seminars/',wait_until='load')
            if response.status==200 and page.locator('#slide-image').count():break
            if attempt==9:raise AssertionError('Published seminar viewer is not available')
            time.sleep(10)
        decks=page.evaluate('window.SEMINAR_DECKS')
        assert len(decks)==3
        assert sum(len(s['frames']) for d in decks for s in d['slides'])==16
        assert page.locator('[data-lang], a[download], iframe').count()==0
        assert page.locator('html').get_attribute('lang')=='ko'
        for width in (1440,390,320):
            page.set_viewport_size({'width':width,'height':960 if width==1440 else 844})
            for d in decks:
                for s in d['slides']:
                    for step,frame in enumerate(s['frames']):
                        page.evaluate('(h)=>location.hash=h',f"#{d['id']}/{s['original']}/{step}")
                        page.wait_for_function("f=>{const i=document.getElementById('slide-image');return i.getAttribute('src')===f&&i.complete&&i.naturalWidth>0}",arg=frame)
                        box=page.locator('.stage').bounding_box();ratio=s['dimensions']['width']/s['dimensions']['height']
                        assert abs(box['width']-box['height']*ratio)<1.1,(width,frame,'aspect ratio')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert not page.locator('#load-error').is_visible()
                        checks.append({'width':width,'deck':d['id'],'slide':s['original'],'step':step,'passed':True})
            page.evaluate("location.hash='#bac/3/0'")
            page.wait_for_function("document.getElementById('build-count').textContent==='단계 1 / 3'")
            page.locator('#next').click();assert page.locator('#build-count').inner_text()=='단계 2 / 3'
            page.locator('#prev').click();assert page.locator('#build-count').inner_text()=='단계 1 / 3'
            page.locator('#zoom').click();assert page.locator('#zoom-dialog').evaluate('(e)=>e.open')
            page.locator('#zoom-close').click()
            page.locator('#fullscreen').click()
            page.wait_for_function("document.fullscreenElement||document.getElementById('player').classList.contains('presentation-mode')")
            page.locator('#fullscreen').click()
            page.locator('#thumbnails-toggle').click();assert page.locator('#thumbnails').is_visible()
            page.locator('#thumbnails-toggle').click()
            if width in (1440,390):page.screenshot(path=str(args.output/f'viewer-{width}.png'),full_page=True)
        page.evaluate("location.hash='#clip-rt/16/0'")
        page.wait_for_function("document.querySelector('#media-layer video')?.readyState>=2")
        page.locator('#motion').click();page.wait_for_function("!document.querySelector('#media-layer video').paused")
        time.sleep(.3)
        assert page.locator('#media-layer video').evaluate('(v)=>v.currentTime>0')
        page.locator('#motion').click();assert page.locator('#media-layer video').evaluate('(v)=>v.paused')
        page.evaluate("location.hash='#vla-cache/2/0'")
        page.wait_for_function("document.getElementById('original-count').textContent==='원본 2 / 21'")
        page.locator('#slide-image').evaluate('(i)=>i.decode()')
        page.screenshot(path=str(args.output/'pdf-native-ratio.png'),full_page=True)
        for url in network:
            clean=url.split('?',1)[0].split('#',1)[0].lower()
            assert not clean.endswith(('.pptx','.ppt','.pdf','.zip','.ttf','.otf','.woff','.woff2')),url
        browser.close()
    report={'mode':'live HTTPS + Chromium','base':base,'passed_states':len(checks),'checks':checks,'errors':errors,
            'original_document_requests':0,'font_file_requests':0,'video_play_pause':True}
    (args.output/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(f"Seminars: {len(checks)}/48 rendered state/viewport checks; JS errors={len(errors)}")
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
