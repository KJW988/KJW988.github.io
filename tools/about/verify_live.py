#!/usr/bin/env python3
"""Exercise the deployed homepage, blog, aliases, and post removal in Chromium."""
import json,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE='https://kjw988.github.io'
OUT=Path('live-check-results');OUT.mkdir(exist_ok=True)

def main():
    checks=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(reduced_motion='reduce',service_workers='block')
        page=context.new_page()
        for attempt in range(12):
            page.goto(BASE+'/',wait_until='load')
            if page.locator('#profile-name').count(): break
            if attempt==11: raise AssertionError('New homepage not visible after deployment')
            time.sleep(10)
        page.close()
        for width in (1440,768,390,320):
            for lang,path in [('ko','/'),('en','/en/')]:
                page=context.new_page()
                page.set_viewport_size({'width':width,'height':960 if width>=768 else 844})
                page.set_default_timeout(10000)
                page.on('pageerror',lambda error:errors.append(str(error)))
                try:
                    response=page.goto(BASE+path,wait_until='load');assert response.status==200
                    assert page.locator('html').get_attribute('lang')==lang
                    assert page.locator('#profile-name').count()==1
                    assert page.locator('iframe, button').count()==0
                    assert page.locator('.research-card').count()==3
                    page.evaluate("async()=>{await Promise.all(Array.from(document.querySelectorAll('img')).map(i=>{i.loading='eager';return i.decode()}))}")
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    if width in (1440,390): page.screenshot(path=str(OUT/f'about-{lang}-{width}.png'),full_page=True)
                    page.goto(BASE+path+'#background',wait_until='load')
                    other='en' if lang=='ko' else 'ko';target='/en/' if other=='en' else '/'
                    page.locator(f'.language[hreflang="{other}"]').click()
                    page.wait_for_url(BASE+target+'#background')
                    assert page.locator('html').get_attribute('lang')==other
                    assert page.evaluate('localStorage.getItem("research-language")')==other
                    page.locator('.research-card h3 a').first.click()
                    page.wait_for_url(BASE+f'/projects/endcache/{other}/')
                    assert page.locator('.paper-link').count()==1
                    page.locator('.blog-back').click();page.wait_for_url(BASE+'/')
                    assert page.locator('#profile-name').is_visible()
                    page.locator('.nav-links a[href="/blog/"]').click();page.wait_for_url(BASE+'/blog/')
                    assert page.locator('#sidebar').count()==1
                    assert '4학기 목표 정리' not in page.locator('body').inner_text()
                    checks.append({'language':lang,'width':width,'passed':True})
                except Exception:
                    errors.append(traceback.format_exc())
                finally:page.close()
        page=context.new_page()
        try:
            for lang,target in [('ko','/'),('en','/en/')]:
                page.goto(BASE+'/');page.evaluate('(v)=>localStorage.setItem("research-language",v)',lang)
                page.goto(BASE+'/about/?from=about#background');page.wait_for_url(BASE+target+'?from=about#background')
            old=context.request.get(BASE+'/posts/4th-semester-goals/')
            assert old.status==404,old.status
            for path in ('/','/en/','/blog/','/archives/','/categories/','/tags/','/feed.xml','/sitemap.xml','/assets/js/data/search.json'):
                response=context.request.get(BASE+path);assert response.status==200,(path,response.status)
                assert '4학기 목표 정리' not in response.text() and '4th-semester-goals' not in response.text(),path
            page.goto(BASE+'/blog/')
            assert page.locator('#sidebar a.nav-link[href="/"]').count()==1
            page.locator('#sidebar a.nav-link[href="/"]').click();page.wait_for_url(BASE+'/')
            assert page.locator('#profile-name').count()==1
        except Exception:errors.append(traceback.format_exc())
        page.close()
        nojs=browser.new_context(java_script_enabled=False)
        page=nojs.new_page()
        try:
            for path,lang in [('/','ko'),('/en/','en')]:
                page.goto(BASE+path);assert page.locator('html').get_attribute('lang')==lang
                assert page.locator('.prose p').count()>=3
            page.goto(BASE+'/about/');page.wait_for_url(BASE+'/')
        except Exception:errors.append(traceback.format_exc())
        nojs.close();browser.close()
    report={'about_home_combinations':checks,'post_removal':'404 and absent from public indexes','errors':errors}
    (OUT/'about-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
