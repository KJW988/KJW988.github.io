#!/usr/bin/env python3
"""정적 한·영 연구 페이지 생성. 기존 블로그 파일은 수정하지 않습니다."""
from pathlib import Path
import csv,html,json,math,shutil,argparse
from content import PAPERS,B
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='https://kjw988.github.io/projects'
esc=html.escape

def L(v,lang):return v.get(lang,'') if isinstance(v,dict) else v

def E(v,lang):return '—' if v is None else esc(str(L(v,lang)))

def T(lang,ko,en):return ko if lang=='ko' else en

def tables(p):
 out=[]
 for m in p.get('cache',[]):
  rows=[[r[0],math.ceil(m['N']/r[0]),str(r[1]) if r[2] is None else f'{r[1]} ± {r[2]}',*r[3:]] for r in m['rows']]
  out.append(dict(title=m['name'],cols=['k','NFE','SR (%)','AG (ms)','E2E (ms)','AG ×','E2E ×'],rows=rows,source=m['source'],full=True))
 return out+[dict(s,cols=[B('설정 / 과업','Configuration / task'),*s['cols']]) for s in p['studies']]

def table_html(s,lang):
 head=''.join(f'<th scope="col">{E(c,lang)}</th>' for c in s['cols'])
 rows=''.join('<tr>'+''.join(f'<td>{E(v,lang)}</td>' for v in r)+'</tr>' for r in s['rows'])
 return f'<article class="table-block"><h3>{E(s["title"],lang)}</h3><div class="table-wrap" role="region" tabindex="0" aria-label="{E(s["title"],lang)}"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div><p class="source">{E(s["source"],lang)}</p></article>'

def nav(lang,slug=''):
 back=f'../../{lang}/index.html' if slug else 'index.html'
 languages=''.join(f'<a class="language" lang="{l}" hreflang="{l}" href="../{l}/index.html"'+(' aria-current="page"' if lang==l else '')+f'>{name}</a>' for l,name in [('ko','한국어'),('en','English')])
 return f'<a class="skip" href="#main">{T(lang,"본문으로 이동","Skip to content")}</a><header><nav class="wrap topnav"><a class="brand" href="{back}"><span class="logo">JK</span>Jiwon Kim <span class="brand-sub">/ {T(lang,"연구 프로젝트","Research projects")}</span></a><div class="languages" aria-label="{T(lang,"언어 선택","Select language")}">{languages}</div></nav></header>'

def footer(lang):
 return f'<footer class="wrap"><div>Jiwon Kim · {T(lang,"국민대학교","Kookmin University")}<br><a href="https://github.com/KJW988">GitHub</a> · <a href="https://kjw988.github.io/">{T(lang,"블로그","Blog")}</a></div><p>{T(lang,"실험 수치는 각 논문의 평가 조건과 함께 제시합니다.<br>설명용 예시는 실제 모델 출력과 구분합니다.","Measurements are shown with their evaluation conditions.<br>Illustrative examples are distinct from model outputs.")}</p><a href="#top">↑ {T(lang,"맨 위로","Top")}</a></footer>'

def shell(lang,title,desc,body,slug='',category='efficiency',data=None):
 asset='../../assets' if slug else '../assets'
 route=f'{BASE}/{slug+"/" if slug else ""}'
 payload='' if data is None else '<script type="application/json" id="paper-data">'+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script>'
 return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · Jiwon Kim</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{route}{lang}/"><link rel="alternate" hreflang="ko" href="{route}ko/"><link rel="alternate" hreflang="en" href="{route}en/"><link rel="alternate" hreflang="x-default" href="{route}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="article"><meta property="og:url" content="{route}{lang}/"><meta name="color-scheme" content="light"><link rel="stylesheet" href="{asset}/site.css"><link rel="icon" href="{asset}/favicon.svg" type="image/svg+xml"><script>document.documentElement.classList.add('js')</script><script src="{asset}/site.js" defer></script></head><body data-category="{category}" id="top">{nav(lang,slug)}{body}{footer(lang)}{payload}</body></html>'''

def paper(p,lang,out):
 slug=p['slug'];author=''.join(f'<span class="{"self" if "Jiwon Kim" in a else "coauthor"}">{esc(a)}</span>' for a in p['authors'])
 links=f'<a class="pill" href="../data-{lang}.csv" download>↓ {T(lang,"실험 데이터","Results CSV")}</a><a class="pill" href="#citation">{T(lang,"논문 정보 · 인용","Paper details · Cite")}</a>'
 if p['code']:links=f'<a class="pill primary" href="{esc(p["code"])}">↗ {T(lang,"공개 코드","Code")}</a>'+links
 if (out/'papers'/f'{slug}.pdf').exists():links=f'<a class="pill primary" href="../../papers/{slug}.pdf">↗ PDF</a>'+links
 metric=''.join(f'<div><strong>{esc(v)}</strong><span>{E(label,lang)}</span></div>' for v,label in p['metrics'])
 figure=''
 if (out/'assets'/f'{slug}.webp').exists():
  figure=f'<figure class="paper-figure"><button class="zoom" type="button" aria-label="{T(lang,"논문 그림 확대","Enlarge paper figure")}"><img src="../../assets/{slug}.webp" alt="{E(p["figure"],lang)}" fetchpriority="high"></button><figcaption>{E(p["figure"],lang)} <span class="zoom-label">⤢ {T(lang,"클릭하여 확대","Click to enlarge")}</span></figcaption></figure>'
 steps=''.join(f'<button class="step" type="button" data-step="{i}" aria-pressed="{str(i==0).lower()}" aria-controls="step-text"><span>0{i+1}</span><b>{E(s[0],lang)}</b></button>' for i,s in enumerate(p['steps']))
 method=''.join(f'<article class="story"><span class="number">0{i+1}</span><div><h3>{E(s[0],lang)}</h3><p>{E(s[1],lang)}</p></div></article>' for i,s in enumerate(p['sections']))
 items=[('overview',T(lang,'개요','Overview')),('method',T(lang,'방법','Method')),('results',T(lang,'실험 결과','Results')),('limits',T(lang,'해석과 한계','Scope & limits')),('citation',T(lang,'인용','Citation'))]
 tabs=''.join(f'<a href="#{k}">{v}</a>' for k,v in items)
 fulltables=''.join(table_html(s,lang) for s in tables(p))
 related=''.join(f'<a class="related" href="../../{r["slug"]}/{lang}/index.html"><strong>{esc(r["name"])} ↗</strong><span>{E(r["lead"],lang)}</span></a>' for r in PAPERS if r['slug']!=slug and (r['category']==p['category'] or r['slug']==('star' if slug=='navila-patch' else 'navila-patch') ))
 body=f'''<main id="main" class="wrap"><section class="hero"><div class="eyebrow">{esc(p['name'])} / {E(p['venue'],lang)}</div><h1>{E(p['title'],lang)}</h1><p class="subtitle">{E(p['subtitle'],lang)}</p><div class="authors">{author}</div><p class="affiliation">{E(p['affiliation'],lang)}</p><p class="authornote">{E(p['authornote'],lang)}</p><div class="links">{links}</div></section><p class="lead">{E(p['lead'],lang)}</p>{figure}<div class="metrics">{metric}</div><p class="note">{E(p['metricnote'],lang)}</p><nav class="section-nav" aria-label="{T(lang,'페이지 목차','On this page')}">{tabs}</nav><section id="overview"><div class="eyebrow">01 / {T(lang,'문제와 접근','Question & approach')}</div><h2>{T(lang,'연구 개요','Overview')}</h2><p class="abstract">{E(p['abstract'],lang)}</p></section><section id="method"><div class="eyebrow">02 / {T(lang,'어떻게 동작할까','How it works')}</div><h2>{T(lang,'방법','Method')}</h2><div class="walkthrough"><div class="walk-head"><span>{T(lang,'단계를 눌러 설명 살펴보기','Select a stage to explore')}</span><span id="step-count">01 / 04</span></div><div class="steps">{steps}</div><p id="step-text" aria-live="polite">{E(p['steps'][0][1],lang)}</p><small>{T(lang,'논문 방법을 설명하는 구성도 · 실제 모델 추론 아님','Explanatory method walk-through · not live inference')}</small></div>{method}</section><section id="results"><div class="eyebrow">03 / {T(lang,'측정된 결과','Measured results')}</div><h2>{T(lang,'실험 결과','Results')}</h2><p>{E(p['intro'],lang)}</p><div id="explorer" class="explorer js-only" aria-label="{T(lang,'결과 탐색기','Results explorer')}"></div><noscript><p class="note">{T(lang,'JavaScript 없이도 아래 전체 결과 표를 읽을 수 있습니다.','Full result tables remain readable without JavaScript.')}</p></noscript><details class="data-details"><summary>{T(lang,'전체 원문 데이터 보기','View all source data')}</summary>{fulltables}</details><p class="note">{T(lang,'—: 해당 조건의 결과가 원문에 보고되지 않음. pp: 퍼센트포인트.','—: result not reported for that condition. pp: percentage points.')}</p></section><section id="limits"><h2>{T(lang,'해석과 한계','Scope & limitations')}</h2><div class="caveat">{E(p['limits'],lang)}</div></section><section id="citation"><div class="section-head"><h2>{T(lang,'논문 정보와 인용','Paper details & citation')}</h2><button class="pill" id="copy" type="button">{T(lang,'BibTeX 복사','Copy BibTeX')}</button></div><p class="formal-title">{esc(p['formal_title'])}</p><p class="source">{E(p['source'],lang)}</p><pre id="bibtex">{esc(p['bibtex'])}</pre><p id="copy-status" role="status"></p><p class="note">{T(lang,'확인되지 않은 DOI·권호·페이지 번호는 넣지 않았습니다.','Unverified DOI, volume and page identifiers are omitted.')}</p></section><section><h2>{T(lang,'함께 살펴볼 연구','Related research')}</h2><div class="related-grid">{related}</div></section></main><dialog id="figure-dialog"><button id="close-dialog" class="pill" type="button">{T(lang,'닫기','Close')} ×</button><img alt="{E(p['figure'],lang)}"><p>{E(p['figure'],lang)}</p></dialog>'''
 return shell(lang,p['name']+' — '+L(p['title'],lang),L(p['abstract'],lang),body,slug,p['category'],p)

def index(lang,out):
 cards=''
 for i,p in enumerate(PAPERS,1):
  href=f'../{p["slug"]}/{lang}/index.html';image=f'../assets/{p["slug"]}.webp'
  cover=f'<img src="{image}" alt="" loading="lazy">' if (out/'assets'/f'{p["slug"]}.webp').exists() else f'<strong>{esc(p["name"])}</strong>'
  search=esc((p['name']+' '+p['title']['ko']+' '+p['title']['en']+' '+' '.join(p['tags'])).lower(),quote=True)
  cards+=f'<article class="card" data-category="{p["category"]}" data-search="{search}"><a class="card-cover" href="{href}" tabindex="-1" aria-hidden="true">{cover}</a><div class="card-body"><div class="eyebrow">0{i} / {E(p["venue"],lang)}</div><h2><a href="{href}">{esc(p["name"])}</a></h2><p>{E(p["lead"],lang)}</p><div class="tags">'+''.join(f'<span>{esc(t)}</span>' for t in p['tags'])+f'</div><a class="card-link" href="{href}">{T(lang,"프로젝트 살펴보기","Explore the project")} <span>↗</span></a></div></article>'
 categories=[('all',T(lang,'전체','All')),('efficiency',T(lang,'추론 효율화','Efficiency')),('perception',T(lang,'상황 이해','Perception')),('robustness',T(lang,'강건성','Robustness')),('control',T(lang,'행동 모델','Control'))]
 filters=''.join(f'<button class="filter" type="button" data-filter="{k}" aria-pressed="{str(k=="all").lower()}">{n}</button>' for k,n in categories)
 refs=' · '.join(f'<a href="{u}">{n}</a>' for n,u in [('Nerfies','https://nerfies.github.io/'),('OpenVLA','https://openvla.github.io/'),('OpenVLA-OFT','https://openvla-oft.github.io/'),('Diffusion Policy','https://diffusion-policy.cs.columbia.edu/')])
 body=f'''<main id="main" class="wrap"><section class="index-hero"><div class="eyebrow">{T(lang,'선택된 연구','Selected research')} / 2024—2026</div><h1>Learning That<br><mark>Moves</mark> Us.</h1><p class="tagline">{T(lang,'배움이 움직임이 되고, 일상이 되도록.','From learning to movement. From movement to everyday life.')}</p><p class="index-intro">{T(lang,'관측을 이해하고, 행동을 개선하고, 실행의 효율과 강건성을 검증합니다. 제1저자·공동 제1저자 논문 6편의 문제의식과 방법, 실험 결과를 살펴보세요.','Understanding observations, improving actions, and evaluating efficiency and robustness. Explore six first- and co-first-authored papers, from research questions to experimental results.')}</p></section><div class="index-heading"><strong>{T(lang,'연구 프로젝트','Research projects')}</strong><span id="result-count" role="status">6 {T(lang,'편의 논문','papers')}</span></div><div class="index-controls js-only"><div class="filters" role="group" aria-label="{T(lang,'연구 분야','Research category')}">{filters}</div><input id="search" type="search" placeholder="{T(lang,'논문·키워드 검색','Search papers or keywords')}" aria-label="{T(lang,'논문·키워드 검색','Search papers or keywords')}"></div><div class="cards">{cards}</div><p id="empty" hidden>{T(lang,'검색 조건에 맞는 논문이 없습니다.','No matching papers.')}</p><section><details><summary>{T(lang,'페이지 구성 참고','Page-design references')}</summary><p class="note">{T(lang,'논문 소개 구조, 성능·효율 비교, 탐색형 설명을 참고했습니다. 코드는 별도로 작성했고 다른 연구의 실험 영상이나 결과를 가져오지 않았습니다.','The research narrative, efficiency comparisons and exploratory explanations are informed by these pages. Code is independently written; no other project’s experimental media or results are reused.')}</p><p class="note">{refs}</p></details></section></main>'''
 return shell(lang,T(lang,'연구 프로젝트','Research projects'),T(lang,'김지원의 제1저자·공동 제1저자 논문 6편','Six first- and co-first-authored papers by Jiwon Kim'),body)

def landing():return '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>연구 프로젝트 · Jiwon Kim</title></head><body><p><a href="ko/index.html">한국어</a> · <a href="en/index.html">English</a></p><script>(()=>{let l='ko';try{if(localStorage.getItem('research-language')==='en')l='en'}catch(_){}location.replace(l+'/index.html'+location.hash)})();</script></body></html>'''

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'projects');args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);(out/'assets').mkdir(exist_ok=True)
 for f in ['site.css','site.js']:shutil.copyfile(HERE/f,out/'assets'/f)
 (out/'assets'/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#22283a"/><text x="32" y="42" text-anchor="middle" font-family="sans-serif" font-size="27" fill="white">JK</text></svg>')
 (out/'index.html').write_text(landing(),encoding='utf-8')
 for lang in ['ko','en']:
  (out/lang).mkdir(exist_ok=True);(out/lang/'index.html').write_text(index(lang,out),encoding='utf-8')
 for p in PAPERS:
  folder=out/p['slug'];folder.mkdir(exist_ok=True);(folder/'index.html').write_text(landing(),encoding='utf-8')
  for lang in ['ko','en']:
   (folder/lang).mkdir(exist_ok=True);(folder/lang/'index.html').write_text(paper(p,lang,out),encoding='utf-8')
   with (folder/f'data-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow([L(p['title'],lang)]);w.writerow([L(p['source'],lang)])
    for s in tables(p):
     w.writerow([]);w.writerow([L(s['title'],lang)]);w.writerow([L(s['source'],lang)]);w.writerow([L(c,lang) for c in s['cols']]);w.writerows([[L(v,lang) if v is not None else 'NA' for v in r] for r in s['rows']])
 urls=[f'{BASE}/{l}/' for l in ['ko','en']]+[f'{BASE}/{p["slug"]}/{l}/' for p in PAPERS for l in ['ko','en']]
 (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc></url>' for u in urls)+'</urlset>',encoding='utf-8')
 print(f'생성 완료: 논문 6편 × 한·영 2종, 목록 2종 → {out}')
if __name__=='__main__':main()
