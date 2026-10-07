#!/usr/bin/env python3
"""Live regression checks for the public portfolio, publication list and retirement."""
import argparse,json,re,sys,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/research'))
from content import PAPERS
from headings import INTRO_KO, publication_title
from publish import paper_url
BASE='https://kjw988.github.io'
EMAIL='zw0831@kookmin.ac.kr'
PROBEE='https://kookmin-sw.github.io/capstone-2024-14/'
CLOSING='이제는 산업 현장에서 동료들과 자유롭게 의견을 나누며, 정해진 답이 없는 문제에 대한 새로운 해결책을 함께 찾아가고자 합니다.'
DENIED=['/blog/','/blog/index.html','/blog/page2/','/posts/4th-semester-goals/','/posts/','/archives/','/categories/','/tags/','/feed.xml','/assets/js/data/search.json']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',default=BASE);parser.add_argument('--output',type=Path,default=Path('live-check-results'));args=parser.parse_args()
    base=args.base.rstrip('/');out=args.output;out.mkdir(exist_ok=True,parents=True)
    errors=[];home=[];papers=[];retired=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(reduced_motion='reduce',permissions=['clipboard-read','clipboard-write'])
        page=context.new_page()
        for attempt in range(12):
            page.goto(base+'/',wait_until='load')
            if page.locator('.about-closing mark').count():break
            if attempt==11:raise AssertionError('Updated homepage not published')
            time.sleep(10)
        page.close()
        for lang,route in [('ko','/'),('en','/en/')]:
            for width in (1440,768,390,320):
                page=context.new_page();page.set_viewport_size({'width':width,'height':960})
                page.on('pageerror',lambda e:errors.append(str(e)))
                try:
                    assert page.goto(base+route,wait_until='load').status==200
                    assert page.locator('.nav-links a[href="/blog/"]').count()==0
                    assert page.locator('.research-nav').inner_text()==('연구 출판물' if lang=='ko' else 'Publications')
                    assert page.locator('.seminars-nav').count()==1
                    mark=page.locator('.about-closing strong mark')
                    assert mark.count()==1 and 'linear-gradient' in mark.evaluate('(e)=>getComputedStyle(e).backgroundImage')
                    if lang=='ko':assert mark.inner_text()==CLOSING
                    assert page.locator('.prose > p').count()==4
                    expected='논문 전체보기(6)' if lang=='ko' else 'View all publications (6)'
                    assert re.sub(r'\s+',' ',page.locator('.publication-heading-link').inner_text()).replace(' ↗','')==expected
                    assert page.locator('#email-app,#email-gmail,.email-hint,#contact .eyebrow').count()==0
                    assert page.locator('#contact h2').inner_text()==('함께 이야기해요.' if lang=='ko' else 'Let’s talk.')
                    page.locator('.email-contact-link').click()
                    page.locator('#copy-email').click()
                    page.wait_for_function('e=>document.getElementById("email-status").textContent.length>0',arg=EMAIL)
                    assert page.evaluate('navigator.clipboard.readText()')==EMAIL
                    awards=page.locator('.award')
                    assert awards.count()==4
                    for i,dest in enumerate([f'/projects/star/{lang}/',f'/projects/lift3d-film/{lang}/',PROBEE,PROBEE]):
                        assert awards.nth(i).locator('a').get_attribute('href')==dest
                        assert len(awards.nth(i).locator('.award-description').inner_text())>10
                    assert '106' in awards.first.inner_text() and '108' not in awards.first.inner_text()
                    page.evaluate("async()=>{await Promise.all([...document.querySelectorAll('img')].map(i=>{i.loading='eager';return i.decode()}))}")
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    if width in (1440,390):
                        for selector,name in [('#about','about'),('#contact','contact'),('#awards','awards'),('#research','home-publications')]:
                            page.locator(selector).screenshot(path=str(out/f'{name}-{lang}-{width}.png'))
                    page.locator('.publication-heading-link').click();page.wait_for_url(base+f'/projects/{lang}/')
                    assert page.locator('.card').count()==6
                    home.append({'lang':lang,'width':width,'passed':True})
                except Exception:errors.append(traceback.format_exc())
                finally:page.close()
            for width in (1440,390,320):
                for slug in ('',*[p['slug'] for p in PAPERS]):
                    page=context.new_page();page.set_viewport_size({'width':width,'height':960});page.set_default_timeout(12000)
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    try:
                        route=f'/projects/{slug+"/" if slug else ""}{lang}/'
                        assert page.goto(base+route,wait_until='load').status==200
                        page.evaluate("async()=>{await Promise.all([...document.querySelectorAll('img[src]')].map(i=>{i.loading='eager';return i.decode()}))}")
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        if not slug:
                            if lang=='ko':assert page.locator('.index-intro').inner_text()==INTRO_KO
                            assert page.locator('.card h2').all_text_contents()==[publication_title(p,lang) for p in PAPERS]
                            if width in (1440,390):page.screenshot(path=str(out/f'publications-{lang}-{width}.png'),full_page=True)
                            page.locator('#search').fill('EndCache');assert page.locator('.card:visible').count()==1
                            page.locator('#search').fill('');page.locator('[data-filter="control"]').click();assert page.locator('.card:visible').count()==2
                        else:
                            p=next(p for p in PAPERS if p['slug']==slug)
                            assert page.locator('h1').inner_text()==publication_title(p,lang)
                            assert page.locator('.paper-link').get_attribute('href')==paper_url(slug)
                            assert page.locator('#method button,.step').count()==0
                            assert page.locator('#method .method-copy p').all_text_contents()==[body[lang] for _,body in p['sections']]
                            page.locator('.zoom').click();assert page.locator('#figure-dialog').evaluate('(e)=>e.open');page.locator('#close-dialog').click()
                            if p['kind']=='cache':
                                page.locator('#cache-model').select_option(index=1);assert page.locator('#cache-values').inner_text()
                            elif slug=='lift3d-film':
                                page.locator('#film-task').select_option(index=0);assert page.locator('.missing').count()==1
                            else:
                                page.locator('#study-select').select_option(index=1);assert page.locator('#study-plot').inner_text()
                            if slug=='star':assert '*' in page.locator('.authornote').inner_text()
                        papers.append({'route':route,'width':width,'passed':True})
                    except Exception:errors.append(traceback.format_exc())
                    finally:page.close()
        page=context.new_page()
        try:
            for path in DENIED:
                response=context.request.get(base+path);assert response.status==404,(path,response.status)
                assert '4학기 목표 정리' not in response.text()
                retired.append({'path':path,'status':response.status})
            for path in ('/','/en/','/projects/ko/','/projects/en/','/seminars/'):
                response=context.request.get(base+path);assert response.status==200
                assert 'href="/blog/' not in response.text()
            page.goto(base+'/');page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined})")
            page.locator('#copy-email').click();assert page.locator('#email-copy-fallback').is_visible()
            assert page.locator('#email-copy-fallback').input_value()==EMAIL
            page.goto(base+'/research/');page.wait_for_url(re.compile(re.escape(base)+r'/projects/(ko|en)/'))
            page.goto(base+'/seminars/');assert page.locator('a[href="/blog/"]').count()==0
            assert page.evaluate('window.SEMINAR_DECKS.length')>=3
            page.goto(base+'/');page.evaluate("async()=>{const c=await caches.open('chirpy-retired-test');await c.put('/blog/',new Response('old blog'))}")
            page.reload();page.wait_for_function("async()=>!(await caches.keys()).includes('chirpy-retired-test')")
        except Exception:errors.append(traceback.format_exc())
        page.close()
        nojs=browser.new_context(java_script_enabled=False);page=nojs.new_page()
        try:
            page.goto(base+'/');assert page.locator('.about-closing mark').is_visible();assert not page.locator('#copy-email').is_visible()
            assert page.locator('.email-address').inner_text()==EMAIL
        except Exception:errors.append(traceback.format_exc())
        browser.close()
    report={'home':home,'publications':papers,'retired':retired,'errors':errors,'scope':'Live published Pages only. Source repository, historical copies and external caches are not made private.'}
    (out/'site-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
