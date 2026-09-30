#!/usr/bin/env python3
"""Check the English site against its Korean counterpart and shared paper copy."""
from __future__ import annotations
import argparse,json,os,re,sys,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/research'))
from presentation import COPY
from headings import INTRO_EN,publication_title
from content import PAPERS


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',default='https://kjw988.github.io')
    ap.add_argument('--output',type=Path,default=Path('live-check-results'))
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    base=a.base.rstrip('/');routes=['/en/','/projects/en/',*[f'/projects/{s}/en/' for s in COPY]]
    report={'mode':'live HTTPS + Chromium','pages':[],'parity':[],'errors':[]}
    def load(page,route):
        response=page.goto(base+route,wait_until='load');assert response.status==200
    with sync_playwright() as pw:
        options={'headless':True}
        if os.getenv('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=pw.chromium.launch(**options)
        context=browser.new_context(reduced_motion='reduce',service_workers='block')
        for width in (1440,768,390,320):
            for route in routes:
                page=context.new_page();page.set_viewport_size({'width':width,'height':960})
                page.on('pageerror',lambda e:report['errors'].append(str(e)))
                try:
                    load(page,route)
                    page.evaluate('document.fonts.ready')
                    assert page.locator('html').get_attribute('lang')=='en'
                    assert page.locator('link[rel="canonical"]').get_attribute('href')==base+route
                    assert page.locator('.nav-links a').all_text_contents()==['About me','Publication','Seminars']
                    assert page.locator('.research-nav').get_attribute('href')=='/projects/en/'
                    assert page.locator('.seminars-nav').get_attribute('href')=='/seminars/'
                    text=page.locator('body').inner_text().replace('한국어','').replace('김지원','')
                    assert not re.search('[가-힣]',text),'Unexpected Korean text in English UI'
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    if route=='/en/':
                        assert 'Machine Intelligence Lab. (MI Lab) | Advisor: Prof. Jaekoo Lee' in text
                        assert 'M.S. Student in Computer Science' in text
                        assert '6th place out of 106 teams' in text
                        assert '108 teams' not in text
                        assert page.locator('.about-closing strong mark').count()==1
                        cards=page.locator('.research-card');assert cards.count()==3
                        for card,slug in zip(cards.all(),('endcache','star','lift3d-film')):
                            assert card.locator('.summary-question').inner_text()==COPY[slug]['question']['en']
                            assert card.locator('.summary-points li').all_text_contents()==COPY[slug]['points']['en']
                        if width in (1440,390):page.locator('.prose').screenshot(path=str(a.output/f'english-about-{width}.png'))
                    elif route=='/projects/en/':
                        assert page.locator('.index-intro').inner_text()==INTRO_EN
                        assert page.locator('.card').count()==6
                        for card,slug in zip(page.locator('.card').all(),COPY):
                            assert card.locator('.summary-question').inner_text()==COPY[slug]['question']['en']
                            assert card.locator('.summary-points li').all_text_contents()==COPY[slug]['points']['en']
                            assert card.locator('.tags span').all_text_contents()==COPY[slug]['tags']
                        assert page.locator('footer a',has_text='Home').get_attribute('href')==base+'/en/'
                        if width in (1440,390):page.screenshot(path=str(a.output/f'english-publication-{width}.png'),full_page=True)
                    else:
                        slug=route.split('/')[2];paper=next(p for p in PAPERS if p['slug']==slug)
                        assert page.locator('h1').inner_text()==publication_title(paper,'en')
                        assert page.locator('#method .method-copy p').all_text_contents()==[body['en'] for _,body in paper['sections']]
                        assert page.locator('.data-details summary').inner_text()=='View full results'
                        assert page.locator('#limits,#citation,a[download]').count()==0
                        assert page.locator('footer a',has_text='Home').get_attribute('href')==base+'/en/'
                        assert page.locator('#results table').count()>0
                        data=json.loads(page.locator('#paper-data').text_content())
                        if width==1440:
                            other=context.new_page();load(other,route.replace('/en/','/ko/'))
                            ko=json.loads(other.locator('#paper-data').text_content());other.close()
                            assert [s['rows'] for s in data['studies']]==[s['rows'] for s in ko['studies']]
                            assert [s['rows'] for s in data.get('cache',[])]==[s['rows'] for s in ko.get('cache',[])]
                            assert [m[0] for m in data['metrics']]==[m[0] for m in ko['metrics']]
                            report['parity'].append({'slug':slug,'shared_numbers':True,'formal_title_preserved':True})
                        if paper['kind']=='cache':page.locator('#cache-model').select_option(index=1)
                        elif slug=='lift3d-film':page.locator('#film-task').select_option(index=0)
                        else:page.locator('#study-select').select_option(index=1)
                        assert page.locator('#explorer').inner_text()
                    ko_route='/' if route=='/en/' else route.replace('/en/','/ko/')
                    assert page.locator('.languages a[hreflang="ko"]').get_attribute('href')==ko_route
                    assert page.locator('.languages a[hreflang="en"]').get_attribute('href')==route
                    page.locator('.languages a[hreflang="ko"]').click();page.wait_for_url(base+ko_route)
                    page.locator('.languages a[hreflang="en"]').click();page.wait_for_url(base+route)
                    if width==1440 and route.startswith('/projects/'):
                        page.locator('footer a',has_text='Home').click();page.wait_for_url(base+'/en/')
                    report['pages'].append({'route':route,'width':width,'passed':True})
                except Exception:report['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                finally:page.close()
        browser.close()
    (a.output/'english-review-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'pages':len(report['pages']),'numeric_parity':len(report['parity']),'errors':report['errors']},ensure_ascii=False))
    if report['errors'] or len(report['pages'])!=32 or len(report['parity'])!=6:raise SystemExit(1)
if __name__=='__main__':main()
