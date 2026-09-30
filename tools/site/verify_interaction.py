#!/usr/bin/env python3
"""Verify coupled highlighter/Us movement and the requested Publication-only removals."""
from __future__ import annotations
import argparse,base64,json,mimetypes,os,time,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from interaction import SLUGS, HOME_SLUGS

def memory_html(site:Path,route:str):
    # Optional, network-free rendering for development; public CI uses HTTPS below.
    from bs4 import BeautifulSoup
    file=site/route.lstrip('/')
    if file.is_dir():file=file/'index.html'
    soup=BeautifulSoup(file.read_text(encoding='utf-8'),'html.parser')
    def resolve(url):
        value=urlsplit(url)
        if value.scheme:return None
        return site/value.path.lstrip('/') if value.path.startswith('/') else file.parent/value.path
    for link in list(soup.select('link[rel="stylesheet"]')):
        path=resolve(link['href']);style=soup.new_tag('style');style.string=path.read_text();link.replace_with(style)
    for image in soup.select('img[src]'):
        path=resolve(image['src'])
        if path and path.is_file():image['src']='data:'+(mimetypes.guess_type(path)[0] or 'application/octet-stream')+';base64,'+base64.b64encode(path.read_bytes()).decode()
    scripts=[]
    for script in list(soup.select('script[src]')):
        path=resolve(script['src']);script.decompose()
        if path and path.name!='privacy-reset.js':scripts.append(path.read_text())
    for text in scripts:
        script=soup.new_tag('script');script.string=text;soup.body.append(script)
    return str(soup)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='https://kjw988.github.io')
    parser.add_argument('--site',type=Path)
    parser.add_argument('--output',type=Path,default=Path('live-check-results'))
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    base=a.base.rstrip('/');results={'mode':'in-memory HTML rendering' if a.site else 'live HTTPS + Chromium','motion':[],'papers':[],'home_cards':[],'errors':[]}
    def load(page,route):
        if a.site:page.set_content(memory_html(a.site,route),wait_until='load')
        else:assert page.goto(base+route,wait_until='load').status==200
    with sync_playwright() as pw:
        opts={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=pw.chromium.launch(**opts)
        if not a.site:
            ready=browser.new_page()
            for i in range(18):
                load(ready,'/projects/ko/')
                if ready.locator('[data-motion-version="push-pull-v2"]').count()==1:break
                if i==17:raise AssertionError('Push/pull build is not yet deployed')
                time.sleep(10)
            ready.close()
        expected={}
        for lang in ('ko','en'):
            reference=browser.new_page();load(reference,f'/projects/{lang}/')
            expected[lang]={}
            for card in reference.locator('.card').all():
                href=card.locator('.paper-title a').get_attribute('href');slug=href.split('/')[1]
                note=card.locator('.summary-note')
                expected[lang][slug]={'question':card.locator('.summary-question').inner_text(),'points':card.locator('.summary-points li').all_text_contents(),'note':note.inner_text() if note.count() else None}
            reference.close()
        for width in (1440,768,390,320):
            for route in ('/','/en/','/projects/ko/','/projects/en/'):
                ctx=browser.new_context(viewport={'width':width,'height':960},reduced_motion='no-preference');p=ctx.new_page()
                p.on('pageerror',lambda e:results['errors'].append(str(e)))
                try:
                    load(p,route)
                    m=p.locator('.moves-mark');u=p.locator('.moves-us');pair=p.locator('.moves-pair')
                    assert m.count()==u.count()==pair.count()==1
                    assert m.evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')=='rgb(240, 207, 85)'
                    assert m.evaluate('(e)=>getComputedStyle(e).fontStyle')=='normal'
                    before=m.bounding_box();u0=u.bounding_box();pair0=pair.bounding_box()
                    m.hover();p.wait_for_timeout(620)
                    snap=pair.evaluate('(e)=>{const m=e.querySelector(".moves-mark"),u=e.querySelector(".moves-us"),x=new DOMMatrixReadOnly(getComputedStyle(m,"::before").transform),r=u.getBoundingClientRect();return {u:{x:r.x,y:r.y,width:r.width,height:r.height},matrix:[x.a,x.b,x.c,x.d,x.e,x.f]}}');u1=snap['u'];matrix=snap['matrix']
                    assert matrix[:4]==[1,0,0,1] and matrix[5]==0,matrix
                    assert m.bounding_box()==before and pair.bounding_box()==pair0
                    assert u1['x']>u0['x']+8,(u0,u1)
                    assert abs((before['x']+before['width']+matrix[4])-u1['x'])<1.1,'Highlighter/Us lost contact'
                    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    p.wait_for_timeout(440)
                    snap2=pair.evaluate('(e)=>{const m=e.querySelector(".moves-mark"),u=e.querySelector(".moves-us"),x=new DOMMatrixReadOnly(getComputedStyle(m,"::before").transform),r=u.getBoundingClientRect();return {u:{x:r.x,y:r.y,width:r.width,height:r.height},tx:x.e}}');u2=snap2['u'];matrix2=snap2['tx']
                    assert u0['x']<u2['x']<u1['x'],'Us must follow the pull, not jump back'
                    assert abs((before['x']+before['width']+matrix2)-u2['x'])<1.1
                    p.wait_for_timeout(540)
                    assert abs(u.bounding_box()['x']-u0['x'])<.1 and m.bounding_box()==before
                    assert not pair.evaluate('(e)=>e.classList.contains("is-moving")')
                    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    results['motion'].append({'route':route,'width':width,'yellow':True,'push_px':u1['x']-u0['x'],'coupled_pull':True,'returned_to_origin':True})
                    if route in ('/','/en/'):
                        lang='en' if route=='/en/' else 'ko'
                        cards=p.locator('.research-card');assert cards.count()==3
                        for i,slug in enumerate(HOME_SLUGS):
                            card=cards.nth(i);item=expected[lang][slug]
                            assert f'/projects/{slug}/{lang}/'==card.locator('h3 a').get_attribute('href')
                            assert card.locator('.summary-question').inner_text()==item['question']
                            assert card.locator('.summary-points li').all_text_contents()==item['points']
                            assert card.locator('.research-copy > p:not(.venue):not(.paper-alias)').count()==0
                            note=card.locator('.summary-note')
                            assert (note.inner_text() if note.count() else None)==item['note']
                        results['home_cards'].append({'route':route,'width':width,'matched_publication':True,'cards':3})
                        if width in (1440,390):p.locator('.research-grid').screenshot(path=str(a.output/f'home-cards-{lang}-{width}.png'))
                    if width in (1440,390) and route in ('/','/projects/ko/'):
                        name='home' if route=='/' else 'publication'
                        p.locator('.catchphrase' if route=='/' else '.index-hero').screenshot(path=str(a.output/f'{name}-yellow-{width}.png'))
                except Exception:results['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                finally:ctx.close()
        reduced=browser.new_context(reduced_motion='reduce',viewport={'width':390,'height':960})
        for route in ('/','/en/','/projects/ko/','/projects/en/'):
            p=reduced.new_page()
            try:
                load(p,route);m=p.locator('.moves-mark');u=p.locator('.moves-us');b=u.bounding_box();m.hover();p.wait_for_timeout(80)
                assert u.bounding_box()==b
                assert m.evaluate('(e)=>getComputedStyle(e,"::before").animationName')=='none'
                assert m.evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')=='rgb(240, 207, 85)'
            except Exception:results['errors'].append(traceback.format_exc())
            p.close()
        reduced.close()
        for width in (1440,390):
            ctx=browser.new_context(viewport={'width':width,'height':960},reduced_motion='reduce')
            for slug in SLUGS:
                for lang in ('ko','en'):
                    route=f'/projects/{slug}/{lang}/';p=ctx.new_page();p.on('pageerror',lambda e:results['errors'].append(str(e)))
                    try:
                        load(p,route)
                        assert p.locator('#limits,#citation,#bibtex,#copy,#copy-status,a[download],a[href="#limits"],a[href="#citation"]').count()==0
                        assert p.locator('meta[name^="citation_"]').count()==0
                        assert p.locator('.section-nav a').all_text_contents()==(['개요','방법','실험 결과'] if lang=='ko' else ['Overview','Method','Results'])
                        assert p.locator('.paper-link').count()==1
                        assert p.locator('#overview,#method,#results,#explorer').count()==4
                        assert p.locator('#results table').count()>0
                        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        if slug in ('endcache','velocity-reuse'):
                            p.locator('#cache-model').select_option(index=1);assert p.locator('#cache-values').inner_text()
                        elif slug=='lift3d-film':
                            p.locator('#film-task').select_option('0');assert p.locator('#film-plot').inner_text()
                        else:
                            p.locator('#study-select').select_option(index=1);assert p.locator('#study-plot').inner_text()
                        p.locator('.zoom').click();assert p.locator('#figure-dialog').evaluate('(e)=>e.open');p.locator('#close-dialog').click()
                        results['papers'].append({'route':route,'width':width,'requested_sections_removed':True,'results_and_links_preserved':True})
                        if slug=='endcache' and lang=='ko':p.screenshot(path=str(a.output/f'paper-clean-{width}.png'),full_page=True)
                    except Exception:results['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                    finally:p.close()
            ctx.close()
        browser.close()
    (a.output/'interaction-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in results.items()},ensure_ascii=False))
    if results['errors'] or len(results['motion'])!=16 or len(results['papers'])!=24 or len(results['home_cards'])!=8:raise SystemExit(1)
if __name__=='__main__':main()
