#!/usr/bin/env python3
"""Check table-first results, poster order, summary counts, media and unchanged data."""
from pathlib import Path
import argparse, base64, hashlib, json, mimetypes, os, re, sys, traceback
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from publication_layout import CACHE, SLUGS, VERSION, number

MEDIA_HASHES = {
 'navila-overview.png': '011285f5ea67e487bd276b072c0d85ad5b2c8eca4841cd7ba70cded18b707e6e',
 'navila-poster.svg': '206ca56918d18327de4de5f85d9a5da344e03b953f93badfa4673b2ef8a59bba',
 'velocity-overview.png': '531e2dfe2993ac2a1858f4a423dce3c7b1c97de6e1621444bdcaa9952b3afeba',
 'velocity-poster.svg': 'fc4d1f62dc08d790ada8d69a0216b1e95a1f0d8cd02337d548b562db0848da83'}
TABLES = {'endcache':4, 'velocity-reuse':4, 'star':0, 'navila-patch':3, 'lift3d-film':1, 'act-cbam':1}

def snapshot(p):
 return {'metrics':[v for v,_ in p['metrics']], 'cache':[(m['name'],m['N'],m['rows']) for m in p.get('cache',[])], 'studies':[s['rows'] for s in p['studies']]}

def expected_rows(d):
 studies=d['studies'];slug=d['slug']
 if slug=='navila-patch':return [(studies[i]['rows']+studies[i+3]['rows'],[2,1,1,1]) for i in range(3)]
 if slug=='lift3d-film':return [(studies[0]['rows'],[1,1,1])]
 if slug=='act-cbam':
  params={r[0]:r[1] for r in studies[1]['rows']}
  return [([r+[params[r[0]]] for r in studies[0]['rows']],[0,0,2])]
 return []

def verify_rows(page,d):
 for index,(rows,digits) in enumerate(expected_rows(d)):
  actual=page.locator('#results table').nth(index).locator('tbody tr:not(.dataset-label)').evaluate_all('(es)=>es.map(e=>[...e.children].map(c=>c.textContent))')
  expected=[[r[0]]+[number(v,digits[i]) for i,v in enumerate(r[1:])] for r in rows]
  assert actual==expected,(d['slug'],index,actual,expected)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--widths',nargs='+',type=int,default=[1440,768,390,320]);ap.add_argument('--base',default='https://kjw988.github.io');ap.add_argument('--site',type=Path);ap.add_argument('--reference',type=Path);ap.add_argument('--output',type=Path,default=Path('live-check-results'));args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 base=args.base.rstrip('/')
 def load(page, route):
  if not args.site:
   assert page.goto(base+route,wait_until='load').status==200
   return
  from bs4 import BeautifulSoup
  path=args.site/route.lstrip('/')/'index.html';soup=BeautifulSoup(path.read_text(),'html.parser')
  def asset(url):
   parsed=urlsplit(url)
   if parsed.scheme:return None
   return args.site/parsed.path.lstrip('/') if parsed.path.startswith('/') else path.parent/parsed.path
  for link in list(soup.select('link[rel="stylesheet"]')):
   f=asset(link['href'])
   if not f or not f.is_file():link.decompose();continue
   tag=soup.new_tag('style');tag.string=f.read_text();link.replace_with(tag)
  for image in soup.select('img[src]'):
   f=asset(image['src'])
   if f and f.is_file():image['src']='data:'+(mimetypes.guess_type(f.name)[0] or 'application/octet-stream')+';base64,'+base64.b64encode(f.read_bytes()).decode()
  scripts=[]
  for script in list(soup.select('script[src]')):
   f=asset(script['src']);script.decompose()
   if f and f.is_file() and f.name!='privacy-reset.js':scripts.append(f.read_text())
  for code in scripts:
   tag=soup.new_tag('script');tag.string=code;soup.body.append(tag)
  page.set_content(str(soup),wait_until='load')
 report={'mode':'local built artifact' if args.site else 'live HTTPS + Chromium','version':VERSION,'pages':[],'indexes':[],'numeric_parity':[],'media':[],'no_js':[],'errors':[]}
 try:
  with sync_playwright() as pw:
   options={'headless':True}
   if os.getenv('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
   browser=pw.chromium.launch(**options);ctx=browser.new_context(reduced_motion='reduce',service_workers='block')
   if args.site:status=json.loads((args.site/'projects/completion-status.json').read_text())
   else:
    resp=ctx.request.get(base+'/projects/completion-status.json');assert resp.status==200;status=resp.json()
   assert status['missing_media']==[]
   for name,digest in MEDIA_HASHES.items():
    if args.site:raw=(args.site/'projects/assets'/status['media'][name]).read_bytes()
    else:
     asset=ctx.request.get(base+'/projects/assets/'+status['media'][name]);assert asset.status==200;raw=asset.body()
    assert hashlib.sha256(raw).hexdigest()==digest
    report['media'].append({'name':name,'sha256':digest})
   pairs={}
   for width in args.widths:
    if width!=args.widths[0]:
     ctx.close();browser.close();browser=pw.chromium.launch(**options);ctx=browser.new_context(reduced_motion='reduce',service_workers='block')
    for slug in SLUGS:
     for lang in ('ko','en'):
      route=f'/projects/{slug}/{lang}/';p=ctx.new_page();p.set_viewport_size({'width':width,'height':960});p.set_default_timeout(6000)
      p.on('pageerror',lambda e:report['errors'].append(str(e)))
      try:
       print('CHECK',width,route,flush=True)
       load(p,route);p.evaluate('document.fonts.ready')
       if slug=='star':
        assert p.locator('main[data-star-public="star-public-header-v1"]').count()==1
        assert p.locator('h1').inner_text().startswith('STAR:')
        assert p.locator('a[href="https://www.autopilot-cvpr.net/"]').count()==1
        assert 'non-archival' in p.locator('main').inner_text().lower()
        assert p.locator('#paper-data,#results,#overview,#analysis,#method,.paper-figure,.metrics,.paper-summary,#poster,#related,#explorer,#figure-dialog,table').count()==0
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert 'star-overview' not in p.content()
        report['pages'].append({'route':route,'width':width,'tables':0,'metadata_only':True,'passed':True})
        continue
       assert p.locator(f'main[data-publication-layout="{VERSION}"]').count()==1
       assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
       assert p.locator('#poster .poster-caption,#results details,#metric-select,#limits,#citation,#bibtex,a[download]').count()==0
       assert p.locator('main > section').last.get_attribute('id')=='related'
       assert p.locator('#related .related').count()>0
       data=json.loads(p.locator('#paper-data').text_content())
       if lang=='ko':pairs[slug]=snapshot(data)
       else:assert snapshot(data)==pairs[slug]
       if width==1440 and lang=='ko':
        if args.reference:
         old=json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>',(args.reference/route.lstrip('/')/'index.html').read_text(),re.S)[1])
        else:
         sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'));from content import PAPERS
         old=next(x for x in PAPERS if x['slug']==slug)
        assert snapshot(old)==snapshot(data);report['numeric_parity'].append(slug)
       assert p.locator('#results table').count()==TABLES[slug]
       assert all(t.is_visible() for t in p.locator('#results table').all());verify_rows(p,data)
       if slug in CACHE:
        assert p.locator('#explorer').count()==1;p.locator('#cache-model').select_option('1');assert p.locator('#cache-values').inner_text()
        p.locator('#cache-k').fill('0');p.locator('#cache-k').dispatch_event('input');assert 'k = 1' in p.locator('#cache-k-output').inner_text()
       else:
        assert p.locator('#explorer,#study-select,#film-task,#film-gamma,#film-beta').count()==0
        assert '결과 탐색기' not in p.locator('#results').inner_text() and 'Results explorer' not in p.locator('#results').inner_text()
       assert p.locator('.paper-link').count()==1
       if slug=='endcache':assert p.locator('#analysis').bounding_box()['y']<p.locator('#method').bounding_box()['y']
       p.locator('.zoom').click();assert p.locator('#figure-dialog').evaluate('e=>e.open');p.locator('#figure-dialog img').evaluate('e=>e.decode()');p.locator('#close-dialog').click()
       if slug in ('velocity-reuse','navila-patch'):
        poster=p.locator('#poster');assert poster.count()==1
        poster.locator('.poster-preview img').scroll_into_view_if_needed();poster.locator('.poster-preview img').evaluate('e=>e.decode()')
        assert poster.bounding_box()['y']<p.locator('#related').bounding_box()['y']
        p.locator('.poster-preview').click();assert p.locator('#poster-dialog').evaluate('e=>e.open')
        initial=p.locator('.poster-stage img').bounding_box()['width'];p.locator('[data-poster-action="in"]').click();assert p.locator('.poster-stage img').bounding_box()['width']>initial*1.3
        p.locator('[data-poster-action="fit"]').click();p.keyboard.press('Escape');assert not p.locator('#poster-dialog').evaluate('e=>e.open')
       if lang=='en':assert not re.search('[가-힣]',p.locator('body').inner_text().replace('한국어','').replace('김지원',''))
       if width==1440 and lang=='ko':
        p.locator('#results').screenshot(path=str(args.output/f'{slug}-results-{width}.png'))
        if slug=='navila-patch':p.screenshot(path=str(args.output/f'{slug}-full-{width}.png'),full_page=True)
       report['pages'].append({'route':route,'width':width,'tables':TABLES[slug],'related_last':True,'passed':True})
      except Exception:
       print(traceback.format_exc(),flush=True);report['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
      finally:p.close()
    for lang in ('ko','en'):
     p=ctx.new_page();p.set_viewport_size({'width':width,'height':960})
     try:
      load(p,f'/projects/{lang}/');p.evaluate('document.fonts.ready')
      assert p.locator('.publication-breakdown dd').evaluate_all('(es)=>es.map(e=>e.firstChild.textContent)')==['1','1','4']
      assert p.locator('.publication-breakdown button,.publication-breakdown a').count()==0
      assert p.locator('.cards .card').count()==6
      assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
      p.locator('.filter[data-filter="efficiency"]').click();assert p.locator('.card:visible').count()==2
      p.locator('.filter[data-filter="all"]').click();p.locator('#search').fill('STAR');assert p.locator('.card:visible').count()==1;p.locator('#search').fill('')
      assert p.locator('.moves-mark').evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')=='rgb(240, 207, 85)'
      if width in (1440,390):p.locator('.index-hero').screenshot(path=str(args.output/f'publication-summary-{lang}-{width}.png'))
      report['indexes'].append({'lang':lang,'width':width,'counts':[1,1,4],'filters_intact':True})
     except Exception:report['errors'].append(traceback.format_exc())
     finally:p.close()
   nojs=browser.new_context(java_script_enabled=False)
   for slug in SLUGS:
    p=nojs.new_page();load(p,f'/projects/{slug}/ko/');assert p.locator('#results table').count()==TABLES[slug];assert all(t.is_visible() for t in p.locator('#results table').all());p.close();report['no_js'].append(slug)
   nojs.close();ctx.close();browser.close()
 finally:
  pass
 (args.output/'publication-layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()},ensure_ascii=False))
 if report['errors'] or len(report['pages'])!=len(args.widths)*12 or len(report['indexes'])!=len(args.widths)*2:raise SystemExit(1)
if __name__=='__main__':main()
