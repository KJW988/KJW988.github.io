#!/usr/bin/env python3
"""Acceptance tests for the complete publication update, not the old explorer contract."""
from pathlib import Path
import argparse,hashlib,json,os,re,sys,traceback
from playwright.sync_api import sync_playwright
from publication_finish import SLUGS,ASSETS,POSTERS,VERSION,MEDIA_HASHES
from publication_finish_copy import METHODS
ROOT=Path(__file__).resolve().parents[2]
def snapshot(p):return {'metrics':[v for v,_ in p['metrics']],'cache':[(m['name'],m['N'],m['rows']) for m in p.get('cache',[])],'studies':[s['rows'] for s in p['studies']]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base',default='https://kjw988.github.io');ap.add_argument('--output',type=Path,default=Path('live-check-results'));ap.add_argument('--reference',type=Path);ap.add_argument('--require-media',action='store_true');a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 report={'pages':[],'numeric_parity':[],'home':[],'media':[],'errors':[],'pending':[]};bilingual={}
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
  b=pw.chromium.launch(**opts);ctx=b.new_context(reduced_motion='reduce',service_workers='block')
  r=ctx.request.get(a.base+'/projects/completion-status.json');assert r.status==200
  status=r.json();report['pending']=status['missing_media']
  for name,filename in status['media'].items():
   data=ctx.request.get(a.base+'/projects/assets/'+filename);assert data.status==200
   digest=hashlib.sha256(data.body()).hexdigest();assert digest.startswith(filename.rsplit('-',1)[1].split('.')[0])
   if name!='star-overview.svg':assert digest==MEDIA_HASHES[name]
   report['media'].append({'asset':name,'sha256':digest,'passed':True})
  for width in (1440,768,390,320):
   for slug in SLUGS:
    for lang in ('ko','en'):
     route=f'/projects/{slug}/{lang}/';p=ctx.new_page();p.set_viewport_size({'width':width,'height':960});p.on('pageerror',lambda e:report['errors'].append(str(e)))
     try:
      assert p.goto(a.base+route,wait_until='load').status==200
      assert p.locator(f'[data-publication-finish="{VERSION}"]').count()==1
      assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
      assert p.locator('h1').count()==1 and p.locator('.language').count()>=1
      assert p.locator('#limits,#citation,#bibtex,a[download]').count()==0
      assert p.locator('.section-nav a[href="#overview"]').inner_text()==('문제 정의' if lang=='ko' else 'Problem')
      if slug in METHODS:assert p.locator('#method .method-copy p').all_text_contents()==[x['body'][lang] for x in METHODS[slug]]
      if slug=='endcache':assert p.locator('.section-nav [href="#analysis"]').count()==1 and p.locator('#analysis').bounding_box()['y']<p.locator('#method').bounding_box()['y']
      d=json.loads(p.locator('#paper-data').text_content());assert not any(x in d for x in ('bibtex','limits','metricnote'))
      if lang=='ko':bilingual[slug]=snapshot(d)
      else:assert snapshot(d)==bilingual[slug]
      if width==1440 and lang=='ko':
       if a.reference:
        old=json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>',(a.reference/route.lstrip('/')/'index.html').read_text(),re.S)[1])
       else:
        sys.path.insert(0,str(ROOT/'tools/research'));from content import PAPERS
        old=next(x for x in PAPERS if x['slug']==slug)
       assert snapshot(d)==snapshot(old);report['numeric_parity'].append(slug)
      if slug=='star':
       assert p.locator('.paper-link,#explorer,.data-details,#poster').count()==0
       assert p.locator('#results table').count()==4
       assert all(p.locator('#results table').nth(i).is_visible() for i in range(4))
       assert 'drive.google.com' not in p.content() and 'Non-archival' in p.locator('body').inner_text()
      else:
       assert p.locator('.paper-link').count()==1 and p.locator('#explorer').count()==1
       if slug in ('velocity-reuse','endcache'):p.locator('#cache-model').select_option('1');assert p.locator('#cache-values').inner_text()
       elif slug=='lift3d-film':p.locator('#film-task').select_option('0');assert p.locator('#film-plot').inner_text()
       else:p.locator('#study-select').select_option('1');assert p.locator('#study-plot').inner_text()
      if slug in ASSETS and ASSETS[slug] in status['media']:assert status['media'][ASSETS[slug]] in p.locator('.paper-figure img').get_attribute('src')
      p.locator('.zoom').click();assert p.locator('#figure-dialog').evaluate('(e)=>e.open');p.locator('#figure-dialog img').evaluate('(e)=>e.decode()');p.locator('#close-dialog').click()
      if slug in POSTERS and POSTERS[slug] in status['media']:
       image=p.locator('.poster-preview img');image.scroll_into_view_if_needed();image.evaluate('(e)=>e.decode()')
       assert image.evaluate('(e)=>Math.abs(e.clientWidth/e.clientHeight - e.naturalWidth/e.naturalHeight)<.01')
       p.locator('.poster-preview').click();assert p.locator('#poster-dialog').evaluate('(e)=>e.open')
       before=p.locator('.poster-stage img').bounding_box();p.locator('[data-poster-action="in"]').click();assert p.locator('.poster-stage img').bounding_box()['width']>before['width']*1.3
       p.locator('[data-poster-action="fit"]').click();p.keyboard.press('Escape');assert not p.locator('#poster-dialog').evaluate('(e)=>e.open')
      text=p.locator('body').inner_text()
      if lang=='en':assert not re.search('[가-힣]',text.replace('한국어','').replace('김지원',''))
      if width in (1440,390) and lang=='ko':p.screenshot(path=str(a.output/f'{slug}-{width}.png'),full_page=True)
      report['pages'].append({'route':route,'width':width,'passed':True})
     except Exception:report['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
     finally:p.close()
  for lang in ('ko','en'):
   p=ctx.new_page();route='/en/' if lang=='en' else '/';p.goto(a.base+route)
   try:
    assert p.locator('.research-card').count()==3 and p.locator('.moves-mark').count()==1
    assert p.locator('.moves-mark').evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')=='rgb(240, 207, 85)'
    assert p.locator('.research-card .summary-note').count()==0
    if lang=='en':assert 'Visiting Scholar' in p.inner_text('body') and 'Visiting Researcher' not in p.inner_text('body')
    assert p.locator('.research-nav,.seminars-nav').count()==2
    if 'star-overview.svg' in status['media']:assert p.locator(f'.research-card img[src*="{status["media"]["star-overview.svg"]}"]').count()==1
    report['home'].append({'lang':lang,'passed':True})
   except Exception:report['errors'].append(traceback.format_exc())
   p.close()
  p=ctx.new_page();p.goto(a.base+'/seminars/');assert '10개 발표자료 · 405장' not in p.inner_text('body');assert p.evaluate('window.SEMINAR_DECKS.length')==10;p.close()
  for route in ('/blog/','/posts/4th-semester-goals/'):
   assert ctx.request.get(a.base+route).status==404
  nojs=b.new_context(java_script_enabled=False);p=nojs.new_page();p.goto(a.base+'/projects/star/ko/');assert p.locator('#results table').count()==4 and p.locator('#results table').first.is_visible();nojs.close();ctx.close();b.close()
 (a.output/'completion-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({'pages':len(report['pages']),'numbers':len(report['numeric_parity']),'pending':report['pending'],'errors':report['errors']},ensure_ascii=False))
 if len(report['pages'])!=48 or len(report['numeric_parity'])!=6 or report['errors'] or (a.require_media and report['pending']):raise SystemExit(1)
if __name__=='__main__':main()
