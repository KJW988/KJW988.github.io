#!/usr/bin/env python3
"""Published-page checks; checks are against rendered DOM, not screenshots alone."""
import argparse,json,os,re,sys,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/research'))
from content import PAPERS
from headings import INTRO_KO,INTRO_EN,publication_title
from presentation import COPY
from publish import paper_url
from polish import SOURCES,SEMINAR_TITLE
EMAIL='zw0831@kookmin.ac.kr'
DENIED=['/blog/','/blog/index.html','/blog/page2/','/posts/4th-semester-goals/','/posts/','/archives/','/categories/','/tags/','/feed.xml','/assets/js/data/search.json']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',default='https://kjw988.github.io');ap.add_argument('--output',type=Path,default=Path('live-check-results'));a=ap.parse_args()
    base=a.base.rstrip('/');a.output.mkdir(exist_ok=True,parents=True)
    checks=[];errors=[];retired=[];motion=[]
    with sync_playwright() as pw:
        options={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=pw.chromium.launch(**options)
        ctx=browser.new_context(reduced_motion='reduce',permissions=['clipboard-read','clipboard-write'])
        ready=ctx.new_page()
        for attempt in range(18):
            ready.goto(base+'/projects/ko/',wait_until='load')
            if ready.locator('.sitewide-header').count() and ready.locator('.summary-points li').count()==18:break
            if attempt==17:raise AssertionError('Expected editorial version not yet deployed')
            time.sleep(10)
        ready.close()
        def navigation(p,lang):
            assert p.locator('.sitewide-header').count()==1
            assert p.locator('.nav-links a').all_text_contents()==['About me','Publication','Seminars' if lang=='en' else '세미나']
            assert p.locator('.research-nav').get_attribute('href')==f'/projects/{lang}/'
            assert p.locator('.seminars-nav').get_attribute('href')=='/seminars/'
            assert '연구 출판물' not in p.content()
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            p.evaluate('scrollTo(0,250)')
            assert abs(p.locator('.sitewide-header').bounding_box()['y'])<1
            p.evaluate('scrollTo(0,0)')
        for lang in ('ko','en'):
            for width in (1440,768,390,320):
                for slug in ('',*COPY):
                    p=ctx.new_page();p.set_viewport_size({'width':width,'height':960});p.set_default_timeout(15000)
                    p.on('pageerror',lambda e:errors.append(str(e)))
                    route=f'/projects/{slug+"/" if slug else ""}{lang}/'
                    try:
                        assert p.goto(base+route,wait_until='load').status==200;navigation(p,lang)
                        assert p.locator('footer p').count()==0
                        assert '페이지 구성 참고' not in p.content() and 'Page-design references' not in p.content()
                        if not slug:
                            assert p.locator('.index-hero .eyebrow').inner_text()=='2024-2026'
                            assert p.locator('.index-intro').inner_text()==(INTRO_KO if lang=='ko' else INTRO_EN)
                            assert p.locator('.index-intro').evaluate('(e)=>getComputedStyle(e).whiteSpace')=='pre-line'
                            cards=p.locator('.card');assert cards.count()==6
                            for i,item in enumerate(COPY.values()):
                                card=cards.nth(i)
                                assert card.locator('.summary-question').inner_text()==item['question'][lang]
                                assert card.locator('.summary-points li').all_text_contents()==item['points'][lang]
                                assert card.locator('.tags span').all_text_contents()==item['tags']
                            note=cards.first.locator('.summary-note');lst=cards.first.locator('.summary-points')
                            assert note.bounding_box()['y']>=lst.bounding_box()['y']+lst.bounding_box()['height']
                            assert p.locator('.card h2').all_text_contents()==[publication_title(x,lang) for x in PAPERS]
                            for query,count in [('Training-free',2),('Adversarial Attack',1),('NaVILA',0)]:
                                p.locator('#search').fill(query);assert p.locator('.card:visible').count()==count
                            p.locator('#search').fill('');p.locator('[data-filter="control"]').click();assert p.locator('.card:visible').count()==2
                            p.locator('[data-filter="all"]').click()
                            p.locator('.moves-mark').hover();assert p.locator('.moves-mark').evaluate('(e)=>getComputedStyle(e,"::before").animationName')=='none'
                            if width in (1440,390):
                                p.evaluate("async()=>{await Promise.all([...document.images].map(i=>{i.loading='eager';return i.decode()}))}")
                                p.screenshot(path=str(a.output/f'publication-{lang}-{width}.png'),full_page=True)
                        else:
                            item=COPY[slug];paper=next(x for x in PAPERS if x['slug']==slug)
                            assert p.locator('h1').inner_text()==publication_title(paper,lang)
                            summary=p.locator('main > .paper-summary')
                            assert summary.locator('.lead').inner_text()==item['question'][lang]
                            assert summary.locator('li').all_text_contents()==item['points'][lang]
                            assert p.locator('.paper-tags span').all_text_contents()==item['tags']
                            assert p.locator('#method .method-copy p').all_text_contents()==[body[lang] for _,body in paper['sections']]
                            assert p.locator('#method button,.paper-summary button').count()==0
                            assert p.locator('.paper-link').get_attribute('href')==paper_url(slug)
                            if item.get('note'):assert summary.locator(':scope > :last-child').inner_text()==item['note'][lang]
                            p.locator('.zoom').click();assert p.locator('#figure-dialog').evaluate('(e)=>e.open');p.locator('#close-dialog').click()
                            if paper['kind']=='cache':p.locator('#cache-model').select_option(index=1);assert p.locator('#cache-values').inner_text()
                            elif slug=='lift3d-film':p.locator('#film-task').select_option(index=0);assert p.locator('.missing').count()==1
                            else:p.locator('#study-select').select_option(index=1);assert p.locator('#study-plot').inner_text()
                            if slug=='star':assert '*' in p.locator('.authornote').inner_text()
                        checks.append({'route':route,'width':width,'passed':True})
                    except Exception:errors.append({'route':route,'width':width,'error':traceback.format_exc()})
                    finally:p.close()
                p=ctx.new_page();p.set_viewport_size({'width':width,'height':960})
                route='/en/' if lang=='en' else '/'
                try:
                    assert p.goto(base+route).status==200;navigation(p,lang)
                    assert p.locator('.prose > p').count()==4 and p.locator('.about-closing strong mark').count()==1
                    assert p.locator('#email-app,#email-gmail').count()==0
                    p.locator('.email-contact-link').click();p.locator('#copy-email').click()
                    p.wait_for_function("document.getElementById('email-status').textContent.length>0")
                    assert p.evaluate('navigator.clipboard.readText()')==EMAIL
                    assert p.locator('.award').count()==4 and p.locator('.award-description').count()==4
                    assert '106' in p.locator('.award').first.inner_text() and '108' not in p.locator('.award').first.inner_text()
                    assert p.locator('.research-card').count()==3
                    if width in (1440,390):p.evaluate('scrollTo(0,0)');p.screenshot(path=str(a.output/f'home-{lang}-{width}.png'))
                    # Direct cross-section navigation no longer requires a detour through home.
                    p.locator('.research-nav').click();p.wait_for_url(base+f'/projects/{lang}/')
                    p.locator('.seminars-nav').click();p.wait_for_url(base+'/seminars/')
                    assert p.locator('h1').inner_text()==SEMINAR_TITLE
                    checks.append({'route':route,'width':width,'passed':True})
                except Exception:errors.append({'route':route,'width':width,'error':traceback.format_exc()})
                finally:p.close()
        p=ctx.new_page()
        try:
            for route in DENIED:
                r=ctx.request.get(base+route);assert r.status==404;retired.append({'route':route,'status':404})
            p.goto(base+'/');p.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined})");p.locator('#copy-email').click()
            assert p.locator('#email-copy-fallback').is_visible() and p.locator('#email-copy-fallback').input_value()==EMAIL
            p.goto(base+'/');p.evaluate("async()=>{const c=await caches.open('chirpy-retired-test');await c.put('/blog/',new Response('old blog'))}")
            p.reload();p.wait_for_function("async()=>!(await caches.keys()).includes('chirpy-retired-test')")
            p.goto(base+'/seminars/');navigation(p,'ko')
            assert p.locator('h1').inner_text()==SEMINAR_TITLE and p.locator('.intro .description').count()==0
            decks=p.evaluate('window.SEMINAR_DECKS')
            for i,d in enumerate(decks):
                p.locator('#deck-select').select_option(str(i)) if p.locator('#deck-select').is_visible() else p.locator('.deck-choice').nth(i).click()
                p.wait_for_function('id=>document.getElementById("seminar-source").dataset.deck===id',arg=d['id'])
                item=SOURCES[d['id']]
                assert p.locator('.source-paper-title').inner_text()==item['title']
                assert p.locator('[data-source="paper"]').get_attribute('href')==item['paper']
                if item.get('project'):assert p.locator('[data-source="project"]').get_attribute('href')==item['project']
            for w in (1440,390):
                p.set_viewport_size({'width':w,'height':960});p.locator('#deck-select').select_option('0') if p.locator('#deck-select').is_visible() else p.locator('.deck-choice').first.click()
                p.wait_for_function("document.getElementById('slide-image').complete")
                p.screenshot(path=str(a.output/f'seminars-{w}.png'),full_page=True)
            seminar_info={'deck_count':len(decks),'slide_count':sum(len(d['slides']) for d in decks),'complete':len(decks)==10,'source_links':len(decks)}
        except Exception:errors.append(traceback.format_exc());seminar_info={'verified':False}
        p.close()
        normal=browser.new_context(reduced_motion='no-preference')
        p=normal.new_page()
        try:
            for route in ('/','/en/','/projects/ko/','/projects/en/'):
                p.goto(base+route);mark=p.locator('.moves-mark');before=mark.bounding_box();mark.hover();p.wait_for_timeout(260)
                assert mark.evaluate('(e)=>getComputedStyle(e,"::before").animationName')=='marker-drive'
                assert mark.bounding_box()==before
                motion.append({'route':route,'text_stable':True,'animation':True})
                if route=='/':p.locator('.catchphrase').screenshot(path=str(a.output/'moves-hover.png'),animations='allow')
                p.mouse.move(0,0)
        except Exception:errors.append(traceback.format_exc())
        normal.close()
        nojs=browser.new_context(java_script_enabled=False);p=nojs.new_page()
        try:
            for lang in ('ko','en'):
                p.goto(base+f'/projects/{lang}/');assert p.locator('.summary-points li').count()==18
            p.goto(base+'/');assert p.locator('.about-closing mark').is_visible() and not p.locator('#copy-email').is_visible()
        except Exception:errors.append(traceback.format_exc())
        nojs.close();browser.close()
    report={'checks':checks,'expected_page_combinations':64,'retired':retired,'motion':motion,'seminars':seminar_info,'errors':errors}
    (a.output/'site-polish-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    if errors or len(checks)!=64 or len(motion)!=4:raise SystemExit(1)
if __name__=='__main__':main()
