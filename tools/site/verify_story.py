#!/usr/bin/env python3
"""Check publication narratives, source footers, exact captions and unchanged results."""
from __future__ import annotations
import argparse,json,os,re,traceback,sys,base64,mimetypes
from urllib.parse import urlsplit
from pathlib import Path
from playwright.sync_api import sync_playwright
from publication_story import STORIES,VERSION,local,apply_story_copy,numerical_snapshot
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/research'))

def memory_html(site,route):
    from bs4 import BeautifulSoup
    file=site/route.lstrip('/')/'index.html'
    soup=BeautifulSoup(file.read_text(),'html.parser')
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
    ap=argparse.ArgumentParser();ap.add_argument('--base',default='https://kjw988.github.io');ap.add_argument('--output',type=Path,default=Path('live-check-results'));ap.add_argument('--reference',type=Path);ap.add_argument('--site',type=Path)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);report={'pages':[],'numeric_parity':[],'errors':[]}
    base=a.base.rstrip('/')
    with sync_playwright() as pw:
        options={'headless':True}
        if os.getenv('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=pw.chromium.launch(**options);context=browser.new_context(reduced_motion='reduce',service_workers='block')
        for width in (1440,768,390,320):
            for slug,story in STORIES.items():
                for lang in ('ko','en'):
                    route=f'/projects/{slug}/{lang}/';page=context.new_page();page.set_viewport_size({'width':width,'height':960});page.on('pageerror',lambda e:report['errors'].append(str(e)))
                    try:
                        if a.site: page.set_content(memory_html(a.site,route),wait_until='load')
                        else: assert page.goto(base+route,wait_until='load').status==200
                        assert page.locator(f'[data-research-story="{VERSION}"]').count()==1
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        assert page.locator('#overview .story-block').count()==len(story['problem'])
                        assert page.locator('#method .method-copy p').all_text_contents()==[local(b['body'],lang) for b in story['method']]
                        assert page.locator('.metrics .metric-source').all_text_contents()==story['metric_refs']
                        assert page.locator('.exp-head p').inner_text()==('원문 실험값 기반 시각화' if lang=='ko' else 'Visualization of reported experimental results')
                        expected=local(story['caption'],lang)
                        actual=page.locator('figcaption').inner_text().split(' ⤢ ')[0]
                        assert actual==expected,(actual,expected)
                        assert page.locator('#limits,#citation,#bibtex,a[download]').count()==0
                        text=page.locator('body').inner_text()
                        for banned in ['원문 표','실제 모델 추론 아님','호출 수 감소와 시간 가속은 다릅니다','로봇 동작 영상이 아닙니다','퍼센트포인트.','not live model inference','Call-count and time speedup are distinct','pp: percentage points.']:
                            assert banned not in text,banned
                        assert page.locator('#results table').count()>0
                        if slug=='endcache':
                            assert page.locator('#analysis').count()==1
                            assert 'signal-to-noise ratio' in page.locator('#analysis').inner_text()
                            assert page.locator('#analysis').bounding_box()['y']<page.locator('#method').bounding_box()['y']
                            assert page.locator('#analysis .story-equation').count()==1
                            assert ('.svg' in page.locator('.paper-figure img').get_attribute('src') or 'data:image/svg+xml' in page.locator('.paper-figure img').get_attribute('src'))
                            for i in range(3):
                                page.locator('#cache-model').select_option(str(i))
                                assert 'Table' in page.locator('#cache-source').inner_text()
                        elif slug=='velocity-reuse':page.locator('#cache-model').select_option('1')
                        elif slug=='lift3d-film':page.locator('#film-task').select_option('0');assert page.locator('.missing').count()==1
                        else:page.locator('#study-select').select_option('1')
                        assert page.locator('#explorer').inner_text()
                        data=json.loads(page.locator('#paper-data').text_content())
                        if width==1440 and lang=='ko':
                            if a.reference:
                                old=json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>',(a.reference/route.lstrip('/')/'index.html').read_text(),re.S)[1])
                            else:
                                from content import PAPERS
                                old=next(p for p in PAPERS if p['slug']==slug)
                            assert numerical_snapshot(data)==numerical_snapshot(old)
                            report['numeric_parity'].append(slug)
                        if lang=='en':assert not re.search('[가-힣]',text.replace('한국어','').replace('김지원',''))
                        page.locator('.zoom').click();assert page.locator('#figure-dialog').evaluate('(e)=>e.open')
                        page.locator('#figure-dialog img').evaluate('(e)=>e.decode()')
                        assert page.locator('#figure-dialog img').evaluate('(e)=>e.complete&&e.naturalWidth>0')
                        page.locator('#close-dialog').click()
                        if width in (1440,390):
                            page.screenshot(path=str(a.output/f'{slug}-{lang}-{width}.png'),full_page=True)
                        report['pages'].append({'slug':slug,'lang':lang,'width':width,'passed':True})
                    except Exception:report['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                    finally:page.close()
        browser.close()
    (a.output/'publication-story-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'pages':len(report['pages']),'numeric_parity':len(report['numeric_parity']),'errors':report['errors']},ensure_ascii=False))
    if len(report['pages'])!=48 or len(report['numeric_parity'])!=6 or report['errors']:raise SystemExit(1)
if __name__=='__main__':main()
