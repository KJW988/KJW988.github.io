#!/usr/bin/env python3
"""Complete the publication UI using verified, rendered-only author media."""
from pathlib import Path
import argparse, hashlib, html, json, re, shutil, zipfile
HERE=Path(__file__).resolve().parent
VERSION='publication-complete-v1'
MEDIA_HASHES={'velocity-overview.png':'531e2dfe2993ac2a1858f4a423dce3c7b1c97de6e1621444bdcaa9952b3afeba','navila-overview.png':'011285f5ea67e487bd276b072c0d85ad5b2c8eca4841cd7ba70cded18b707e6e','velocity-poster.svg':'fc4d1f62dc08d790ada8d69a0216b1e95a1f0d8cd02337d548b562db0848da83','navila-poster.svg':'206ca56918d18327de4de5f85d9a5da344e03b953f93badfa4673b2ef8a59bba'}
SLUGS=('endcache','velocity-reuse','star','navila-patch','lift3d-film','act-cbam')
ASSETS={'velocity-reuse':'velocity-overview.png','navila-patch':'navila-overview.png'}
POSTERS={'velocity-reuse':'velocity-poster.svg','navila-patch':'navila-poster.svg'}
def E(s):return html.escape(str(s),quote=True)
def L(x,lang):return x[lang] if isinstance(x,dict) else str(x)
def once(s,p,r):
 s,n=re.subn(p,r,s,count=1,flags=re.S)
 if n!=1:raise ValueError('Missing anchor: '+p)
 return s

def prepare_media(site,media):
 bundle=media/'publication-rendered-media.zip'
 if bundle.is_file():
  with zipfile.ZipFile(bundle) as z:
   for name,sha in MEDIA_HASHES.items():
    raw=z.read(name)
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Media integrity: '+name)
    (media/name).write_bytes(raw)
 targets={}
 for name in MEDIA_HASHES:
  src=media/name
  if src.exists():
   raw=src.read_bytes()
   if src.name==name and hashlib.sha256(raw).hexdigest()!=MEDIA_HASHES[name]:raise ValueError('Media hash: '+name)
   if name.endswith('.svg') and any(t in raw for t in (b'<text',b'<script',b'@font-face',b'file://')):raise ValueError('Unsafe SVG: '+name)
   target=Path(name).stem+'-'+hashlib.sha256(raw).hexdigest()[:12]+Path(name).suffix
   (site/'projects/assets'/target).write_bytes(raw);targets[name]=target
 return targets

def table(study,lang,index):
 cols=study['cols'];digits=study.get('digits',3)
 header='<th scope="col">'+('구성' if lang=='ko' else 'Configuration')+'</th>'+''.join('<th scope="col">'+E(L(c,lang))+' ↑</th>' for c in cols)
 rows=[]
 for row in study['rows']:
  cells='<th scope="row">'+E(L(row[0],lang))+'</th>'+''.join('<td>'+('—' if n is None else f'{n:.{digits}f}' if isinstance(n,(int,float)) else E(L(n,lang)))+'</td>' for n in row[1:])
  rows.append('<tr'+(' class="selected-result"' if row is study['rows'][-1] else '')+'>'+cells+'</tr>')
 return '<article class="table-block static-study"><h3>'+E(L(study['title'],lang))+'</h3><div class="table-scroll" tabindex="0" role="region" aria-label="'+E(L(study['title'],lang))+'"><table><thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p class="source">Table '+str(index+2)+'</p></article>'

def poster_html(slug,lang,asset):
 title=('IEIE 2026' if slug=='velocity-reuse' else 'IPIU 2026')+' · '+('발표 포스터' if lang=='ko' else 'Presentation poster')
 label='포스터 확대' if lang=='ko' else 'Enlarge poster'
 note='한국어 발표 포스터' if lang=='ko' else 'Poster presented in Korean'
 return '<section id="poster" class="poster-section"><h2>'+('발표 포스터' if lang=='ko' else 'Poster')+'</h2><button class="poster-preview" type="button" aria-label="'+label+'"><img src="/projects/assets/'+asset+'" alt="'+E(title)+'" loading="lazy" decoding="async" width="2384" height="3370"><span>'+label+' ↗</span></button><dialog id="poster-dialog" class="poster-dialog" aria-label="'+E(title)+'"><div class="poster-toolbar"><strong>'+E(title)+'</strong><div><button type="button" data-poster-action="out" aria-label="'+('축소' if lang=='ko' else 'Zoom out')+'">−</button><button type="button" data-poster-action="fit">'+('맞춤' if lang=='ko' else 'Fit')+'</button><button type="button" data-poster-action="in" aria-label="'+('확대' if lang=='ko' else 'Zoom in')+'">+</button><button type="button" data-poster-action="close">'+('닫기' if lang=='ko' else 'Close')+'</button></div></div><div class="poster-stage" tabindex="0"><img src="/projects/assets/'+asset+'" alt="'+E(title)+'"></div></dialog></section>'

def refine(site,media):
 site=Path(site);media=Path(media);media.mkdir(parents=True,exist_ok=True)
 targets=prepare_media(site,media)
 css=(HERE/'publication_finish.css').read_bytes();css_name='publication-finish-'+hashlib.sha256(css).hexdigest()[:12]+'.css';(site/'projects/assets'/css_name).write_bytes(css)
 posterjs=(HERE/'poster.js').read_bytes();js_name='poster-'+hashlib.sha256(posterjs).hexdigest()[:12]+'.js';(site/'projects/assets'/js_name).write_bytes(posterjs)
 jsp=site/'projects/assets/site.js';js=jsp.read_text();js=js.replace('if(p){\n const root=',"if(p && q('#explorer')){\n const root=")
 js=re.sub(r"const copy=q\('#copy'\);.*?(?=const zoom=q\('\.zoom'\))",'',js,flags=re.S)
 jsp.write_text(js)
 report={'version':VERSION,'pages':[],'media':targets,'missing_media':[x for x in MEDIA_HASHES if x not in targets]}
 for path in site.rglob('*.html'):
  s=path.read_text();rel=path.relative_to(site).as_posix()
  if 'data-publication-finish="'+VERSION+'"' in s:continue
  for slug,name in ASSETS.items():
   if name in targets:s=s.replace(slug+'.webp',targets[name])
  m=re.search(r'<script type="application/json" id="paper-data">(.*?)</script>',s,re.S)
  if m:
   p=json.loads(m[1]);slug=p['slug'];lang='en' if '/en/' in rel else 'ko';before=json.dumps([p['metrics'],p.get('cache'),p['studies']],sort_keys=True)
   for key in ('bibtex','bibauthors','bibvenue','limits','metricnote'):p.pop(key,None)
   p['completion_version']=VERSION
   assert before==json.dumps([p['metrics'],p.get('cache'),p['studies']],sort_keys=True)
   payload=json.dumps(p,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
   s=once(s,r'(<script type="application/json" id="paper-data">).*?(</script>)',lambda m:m[1]+payload+m[2])
   if slug in POSTERS and POSTERS[slug] in targets:
    s=s.replace('</main>',poster_html(slug,lang,targets[POSTERS[slug]])+'</main>',1)
    s=s.replace('</body>','<script src="/projects/assets/'+js_name+'" defer></script></body>')
   nav=[('overview','문제 정의' if lang=='ko' else 'Problem')]
   if slug=='endcache':nav.append(('analysis','분석' if lang=='ko' else 'Analysis'))
   nav.extend([('method','방법' if lang=='ko' else 'Method'),('results','실험 결과' if lang=='ko' else 'Results')])
   if slug in POSTERS and POSTERS[slug] in targets:nav.append(('poster','포스터' if lang=='ko' else 'Poster'))
   s=once(s,r'(<nav[^>]*class="section-nav"[^>]*>).*?(</nav>)',lambda m:m[1]+''.join('<a href="#'+a+'">'+b+'</a>' for a,b in nav)+m[2])
   s=s.replace('</head>','<link rel="stylesheet" href="/projects/assets/'+css_name+'"></head>',1)
   s=s.replace('<main ','<main data-publication-finish="'+VERSION+'" ',1)
   report['pages'].append({'slug':slug,'lang':lang,'static_results':slug=='star','poster':slug in POSTERS and POSTERS[slug] in targets,'new_figure':slug in ASSETS and ASSETS[slug] in targets})
  s=re.sub(r'CVPR Workshop\s*·\s*2026','AUTOPILOT Workshop @ CVPR 2026 · Non-archival',s)
  s=re.sub(r'(src="[^"<>]*assets/site\.js)(?:\?[^"<>]*)?',r'\1?v='+VERSION,s)
  path.write_text(s)
 manifest=site/'projects/sources.json'
 if manifest.exists():
  d=json.loads(manifest.read_text());d.get('paper_links',{}).pop('star',None);manifest.write_text(json.dumps(d,ensure_ascii=False,indent=2))
 for path in (site/'projects/star').rglob('*.html'):
  if 'drive.google.com' in path.read_text():raise ValueError('STAR source link remains: '+str(path))
 (site/'projects/completion-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--site',type=Path,required=True);ap.add_argument('--media',type=Path,default=HERE/'media');a=ap.parse_args();refine(a.site,a.media)
