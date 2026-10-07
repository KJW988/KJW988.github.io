#!/usr/bin/env python3
"""Check impulse/spring motion, responsive rendering and existing publication UI."""
from __future__ import annotations
import argparse,base64,datetime,json,mimetypes,os,subprocess,time,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from interaction import SLUGS, HOME_SLUGS


def memory_html(site:Path,route:str):
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


def core_check():
    js=Path(__file__).with_name('motion-physics.js')
    code=r'''
const assert=require('node:assert/strict');
const {create,advance,STEP}=require(process.argv[1]);
const results=[];
for(const gap of [4,8,12,20]) for(const travel of [8,24,48,64]) {
  const s=create(gap,travel);let lag=false,impulse=false,max=0;
  for(let n=0;n<1000;n++){
    const before={...s};advance(s);
    assert([s.x,s.v,s.u,s.w].every(Number.isFinite));
    assert(s.x<=gap+s.u+1e-7, 'interpenetration');
    if(!before.attached&&!s.attached) assert.equal(s.u,0,'word moved before contact');
    if(!before.attached&&s.attached) impulse=s.v<before.v&&s.w>0;
    if(s.t>.42&&s.v<0&&s.w>0)lag=true;
    max=Math.max(max,s.u);
  }
  assert(impulse&&lag,'missing momentum transfer or return inertia');
  assert(s.quiet>.075&&Math.abs(s.x)<.035&&Math.abs(s.u)<.035,'unsettled');
  assert(max<travel*1.4+gap*.2,'excessive travel');
  results.push({gap,travel,impulse,lag,settled:true});
}
// A fixed integrator must give the same trajectory at different display rates.
const snapshots=[];
for(const hz of [30,60,120,144]){
  const s=create(12,48);let acc=0;
  for(let frame=0;frame<hz*2;frame++){
    acc+=1/hz;while(acc+1e-12>=STEP){advance(s);acc-=STEP;}
  }
  snapshots.push([s.x,s.u,s.v,s.w]);
}
for(const v of snapshots)for(let j=0;j<v.length;j++)assert(Math.abs(v[j]-snapshots[0][j])<1e-8);
console.log(JSON.stringify({cases:results,refresh_rates:[30,60,120,144]}));
'''
    return json.loads(subprocess.check_output(['node','-e',code,str(js)],text=True))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',default='https://kjw988.github.io');ap.add_argument('--site',type=Path)
    ap.add_argument('--output',type=Path,default=Path('live-check-results'))
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    base=a.base.rstrip('/')
    results={'mode':'in-memory HTML' if a.site else 'live HTTPS + Chromium',
             'physics':core_check(),'motion':[],'papers':[],'home_cards':[],'accessibility':[],'errors':[]}
    def load(p,route):
        if a.site:p.set_content(memory_html(a.site,route),wait_until='load')
        else:assert p.goto(base+route,wait_until='load').status==200
    with sync_playwright() as pw:
        opts={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=pw.chromium.launch(**opts)
        if not a.site:
            p=browser.new_page()
            for i in range(18):
                load(p,'/projects/ko/')
                if p.locator('[data-motion-version="spring-contact-v3"]').count()==1:break
                if i==17:raise AssertionError('Physics motion is not yet deployed')
                time.sleep(10)
            p.close()
        expected={}
        for lang in ('ko','en'):
            p=browser.new_page();load(p,f'/projects/{lang}/');expected[lang]={}
            for card in p.locator('.card').all():
                slug=card.locator('.paper-title a').get_attribute('href').split('/')[1]
                expected[lang][slug]=card.locator('.paper-summary').inner_text()
                if slug=='endcache':
                    note=card.locator('.summary-note').inner_text()
                    assert note==('(Velocity Reuse 후속 연구)' if lang=='ko' else '(Follow-up to Velocity Reuse)')
                    expected[lang][slug]=expected[lang][slug].replace(note,'').rstrip()
            p.close()
        for width in (1440,768,390,320):
            for route in ('/','/en/','/projects/ko/','/projects/en/'):
                ctx=browser.new_context(viewport={'width':width,'height':960},reduced_motion='no-preference')
                p=ctx.new_page();p.on('pageerror',lambda e:results['errors'].append(str(e)))
                try:
                    load(p,route)
                    m=p.locator('.moves-mark');u=p.locator('.moves-us');pair=p.locator('.moves-pair')
                    assert m.count()==u.count()==pair.count()==1
                    assert m.evaluate('(e)=>getComputedStyle(e,"::before").backgroundColor')=='rgb(240, 207, 85)'
                    assert m.evaluate('(e)=>getComputedStyle(e).fontStyle')=='normal'
                    before=m.bounding_box();u0=u.bounding_box();pair0=pair.bounding_box();gap=u0['x']-before['x']-before['width']
                    p.clock.install(time=datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc))
                    p.clock.pause_at(datetime.datetime(2026,1,1,0,0,1,tzinfo=datetime.timezone.utc))
                    p.evaluate('''()=>{window.__trace=[];const pair=document.querySelector('.moves-pair'),m=pair.querySelector('.moves-mark'),u=pair.querySelector('.moves-us');function sample(){const x=new DOMMatrixReadOnly(getComputedStyle(m,'::before').transform),y=new DOMMatrixReadOnly(getComputedStyle(u).transform);window.__trace.push({x:x.e,u:y.e,rigid:[x.a,x.b,x.c,x.d,x.f,y.a,y.b,y.c,y.d,y.f],overflow:document.documentElement.scrollWidth>innerWidth+1});if(window.__trace.length<160)requestAnimationFrame(sample);}requestAnimationFrame(sample);}''')
                    m.dispatch_event('pointerenter');p.clock.run_for(2500)
                    trace=p.evaluate('window.__trace')
                    assert len(trace)>100
                    assert all(t['rigid']==[1,0,0,1,0,1,0,0,1,0] for t in trace)
                    assert all(not t['overflow'] and t['x']<=gap+t['u']+.06 for t in trace)
                    assert max(t['u'] for t in trace)>6
                    assert any(b['x']<aa['x']-.02 and b['u']>aa['u']+.02 for aa,b in zip(trace,trace[1:])),'missing return inertia'
                    assert m.bounding_box()==before and pair.bounding_box()==pair0
                    assert abs(u.bounding_box()['x']-u0['x'])<.1
                    assert not pair.evaluate('(e)=>e.classList.contains("is-moving")')
                    results['motion'].append({'route':route,'width':width,'yellow':True,'push_px':round(max(t['u'] for t in trace),2),'inertial_return':True,'rigid_shapes':True,'settled':True})
                    if route in ('/','/en/'):
                        lang='en' if route=='/en/' else 'ko';cards=p.locator('.research-card');assert cards.count()==3
                        for i,slug in enumerate(HOME_SLUGS):
                            card=cards.nth(i)
                            assert card.locator('.paper-summary').inner_text()==expected[lang][slug]
                            assert card.locator('h3 a').get_attribute('href')==f'/projects/{slug}/{lang}/'
                            if slug=='endcache':assert card.locator('.summary-note').count()==0
                        if lang=='en':
                            assert 'University of California, Irvine · Visiting Scholar' in p.locator('body').inner_text()
                            assert 'Visiting Researcher' not in p.locator('body').inner_text()
                        results['home_cards'].append({'route':route,'width':width,'matched_publication':True,'home_followup_note_removed':True})
                    if width in (1440,390) and route in ('/','/projects/ko/'):
                        p.locator('.catchphrase' if route=='/' else '.index-hero').screenshot(path=str(a.output/f'{"home" if route=="/" else "publication"}-yellow-{width}.png'))
                except Exception:results['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                finally:ctx.close()
        for reduced in (True,False):
            ctx=browser.new_context(viewport={'width':390,'height':960},is_mobile=True,has_touch=True,reduced_motion='reduce' if reduced else 'no-preference')
            p=ctx.new_page()
            try:
                load(p,'/');m=p.locator('.moves-mark');pair=p.locator('.moves-pair')
                p.clock.install(time=datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc))
                p.clock.pause_at(datetime.datetime(2026,1,1,0,0,1,tzinfo=datetime.timezone.utc))
                m.dispatch_event('click');p.clock.run_for(250)
                assert pair.evaluate('(e)=>e.classList.contains("is-moving")') is (not reduced)
                p.clock.run_for(2500)
                assert not pair.evaluate('(e)=>e.classList.contains("is-moving")')
                m.dispatch_event('keydown',{'key':'Enter'});p.clock.run_for(200)
                assert pair.evaluate('(e)=>e.classList.contains("is-moving")') is (not reduced)
                p.clock.run_for(2500)
                results['accessibility'].append({'reduced_motion':reduced,'tap_and_keyboard':True})
            except Exception:results['errors'].append(traceback.format_exc())
            finally:ctx.close()
        for width in (1440,390):
            ctx=browser.new_context(viewport={'width':width,'height':960},reduced_motion='reduce')
            for slug in SLUGS:
                for lang in ('ko','en'):
                    route=f'/projects/{slug}/{lang}/';p=ctx.new_page();p.on('pageerror',lambda e:results['errors'].append(str(e)))
                    try:
                        load(p,route)
                        assert p.locator('#limits,#citation,#bibtex,#copy,#copy-status,a[download],a[href="#limits"],a[href="#citation"],meta[name^="citation_"]').count()==0
                        assert p.locator('.section-nav a').all_text_contents()==(['개요','방법','실험 결과'] if lang=='ko' else ['Overview','Method','Results'])
                        assert p.locator('.paper-link').count()==1 and p.locator('#results table').count()>0
                        assert p.locator('#overview,#method,#results,#explorer').count()==4
                        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        if slug in ('endcache','velocity-reuse'):p.locator('#cache-model').select_option(index=1);assert p.locator('#cache-values').inner_text()
                        elif slug=='lift3d-film':p.locator('#film-task').select_option('0');assert p.locator('#film-plot').inner_text()
                        else:p.locator('#study-select').select_option(index=1);assert p.locator('#study-plot').inner_text()
                        p.locator('.zoom').click();assert p.locator('#figure-dialog').evaluate('(e)=>e.open');p.locator('#close-dialog').click()
                        results['papers'].append({'route':route,'width':width,'removals_results_links_preserved':True})
                    except Exception:results['errors'].append({'route':route,'width':width,'error':traceback.format_exc()})
                    finally:p.close()
            ctx.close()
        browser.close()
    (a.output/'interaction-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in results.items() if k!='physics'},ensure_ascii=False))
    if results['errors'] or len(results['motion'])!=16 or len(results['papers'])!=24 or len(results['home_cards'])!=8:raise SystemExit(1)
if __name__=='__main__':main()
