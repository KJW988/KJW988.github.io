#!/usr/bin/env python3
"""논문 6편의 독립적인 한·영 정적 페이지를 생성합니다. 외부 패키지가 필요 없습니다."""
from __future__ import annotations
import argparse
import csv
import html
import io
import json
import math
from pathlib import Path
import shutil
from content import PROJECTS, table, bi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'https://kjw988.github.io/projects'
E = html.escape

def local(value, lang):
    return value.get(lang, '') if isinstance(value, dict) else value

def text(value, lang):
    v=local(value,lang)
    return '—' if v is None else E(str(v))

def choose(lang,ko,en): return ko if lang=='ko' else en

def labels(lang):
    return dict(zip(['all','abstract','method','results','limits','citation'],choose(lang,['전체 논문','연구 개요','방법','실험 결과','해석과 한계','인용'],['All papers','Overview','Method','Results','Scope & limits','Citation'])))

def table_html(tb,lang):
    heads=local(tb['headers'],lang)
    th=''.join(f'<th scope="col">{text(x,lang)}</th>' for x in heads)
    body=''.join('<tr>'+''.join(f'<td>{text(v,lang)}</td>' for v in row)+'</tr>' for row in tb['rows'])
    note=f'<p class="note">{text(tb["note"],lang)}</p>' if local(tb.get('note',''),lang) else ''
    return f'<div class="table-block"><h3>{text(tb["title"],lang)}</h3><div class="table-scroll" role="region" tabindex="0" aria-label="{text(tb["title"],lang)}"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div><p class="source">{text(tb["source"],lang)}</p>{note}</div>'

def extra_tables(p):
    out=[]
    if 'cache_data' in p:
        for m in p['cache_data']:
            rows=[]
            for r in m['rows']:
                sr=str(r[1]) if r[2] is None else f'{r[1]:.1f} ± {r[2]:.1f}'
                rows.append([r[0],math.ceil(m['N']/r[0]),sr,*r[3:]])
            out.append(table(m['name'],bi(['k','호출 수','성공률 (%)','AG (ms)','전체 (ms)','AG ×','전체 ×'],['k','NFE','Success (%)','AG (ms)','E2E (ms)','AG ×','E2E ×']),rows,m['source']))
    if 'patch_data' in p:
        studies=[('type',bi('생성 방식','Construction')),('size',bi('크기','Size')),('exposure',bi('노출 방식','Exposure'))]
        for dataset,group in p['patch_data'].items():
            for n,(key,name) in enumerate(studies,1):
                title=bi(dataset+' · '+name['ko'],dataset+' · '+name['en'])
                out.append(table(title,['Method','NE (m)','OS (%)','SR (%)','SPL (%)'],group[key],bi(f'원문 표 {n}',f'Table {n}')))
    if 'star_data' in p:
        for s in p['star_data'][1:]:
            out.append(table(s['label'],['Method']+s['metrics'],s['rows'],s['source']))
    return out

def header(lang,slug=None):
    home=f'../../{lang}/index.html' if slug else 'index.html'
    language=''.join(f'<a class="language-link" href="../{l}/index.html" hreflang="{l}" lang="{l}"'+(' aria-current="page"' if l==lang else '')+f'>{name}</a>' for l,name in [('ko','한국어'),('en','English')])
    return f'<a class="skip" href="#main">{choose(lang,"본문으로 이동","Skip to content")}</a><header class="topbar"><nav class="nav wrap" aria-label="{choose(lang,"주 탐색","Main navigation")}"><a class="brand" href="{home}"><span class="monogram" aria-hidden="true">JK</span><span>Jiwon Kim <span class="nav-name">/ {choose(lang,"연구 프로젝트","Research projects")}</span></span></a><div class="lang" aria-label="{choose(lang,"언어 선택","Language selection")}">{language}</div></nav></header>'

def shell(lang,title,description,content,slug=None,category='efficiency',data=None):
    asset='../../assets' if slug else '../assets'
    url=f'{BASE}/{slug+"/" if slug else ""}{lang}/'
    alt=f'{BASE}/{slug+"/" if slug else ""}'
    script='' if not data else '<script type="application/json" id="project-data">'+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script>'
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>{E(title)} · Jiwon Kim</title><meta name="description" content="{E(description)}"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ko" href="{alt}ko/"><link rel="alternate" hreflang="en" href="{alt}en/"><link rel="alternate" hreflang="x-default" href="{alt}"><meta property="og:type" content="article"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{url}"><meta property="og:locale" content="{'ko_KR' if lang=='ko' else 'en_US'}"><link rel="icon" href="{asset}/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{asset}/site.css"><script>document.documentElement.classList.add('js');</script><script src="{asset}/site.js" defer></script></head><body data-category="{category}" id="top">{header(lang,slug)}{content}{script}</body></html>'''

def footer(lang):
    return f'''<footer class="footer wrap"><div class="footer-row"><div>Jiwon Kim · {choose(lang,'국민대학교','Kookmin University')}<br><a href="https://github.com/KJW988">GitHub</a> · <a href="https://kjw988.github.io/">{choose(lang,'블로그','Blog')}</a></div><div>{choose(lang,'실험 수치: 저자 제공 논문 · 상호작용: 결과 탐색 및 방법 설명','Measurements: author-provided papers · Interactions: result exploration and method explanation')}<br>{choose(lang,'원문에 보고된 결과와 설명용 예시를 구분합니다.','Reported results are distinguished from illustrative examples.')}</div><a class="backtop" href="#top">↑ {choose(lang,'맨 위로','Back to top')}</a></div></footer>'''

def media_html(p,lang):
    if not p.get('media'): return ''
    blocks=[]
    for m in p['media']:
        src=E(m['src'],quote=True)
        caption=text(m['caption'],lang)
        if m['kind']=='video': element=f'<video controls playsinline preload="none" aria-label="{caption}"><source src="{src}"></video>'
        else: element=f'<a href="{src}"><img src="{src}" alt="{caption}" loading="lazy"></a>'
        blocks.append(f'<figure>{element}<figcaption>{caption}</figcaption></figure>')
    return f'<section class="section" id="media"><h2>{choose(lang,"연구 자료","Research media")}</h2><div class="media-grid">'+''.join(blocks)+'</div></section>'

def page(p,lang):
    l=labels(lang)
    authors=''.join(f'<span class="{"self" if "Jiwon Kim" in a else "coauthor"}">{E(a)}</span>' for a in p['authors'])
    link_html=''.join(f'<a class="pill primary" href="{E(link["url"],quote=True)}">↗ {text(link["label"],lang)}</a>' for link in p['links'])
    link_html+=f'<a class="pill" href="../data-{lang}.csv" download>↓ {choose(lang,"실험 데이터","Results CSV")}</a><a class="pill" href="#citation">{choose(lang,"논문 정보 · 인용","Paper details · Cite")}</a>'
    metrics=''.join(f'<div class="metric"><strong>{E(v)}</strong><span>{text(k,lang)}</span></div>' for k,v in p['metrics'])
    steps=''.join(f'<button type="button" class="step" data-step="{i}" aria-pressed="{str(i==0).lower()}" aria-controls="step-description"><b>0{i+1}</b><span>{text(s[0],lang)}</span></button>' for i,s in enumerate(p['steps']))
    nav=''.join(f'<a href="#{key}">{l[key]}</a>' for key in ['abstract','method','results','limits','citation'])
    stories=''.join(f'<article class="story"><div class="story-num">0{i+1}</div><div><h3>{text(s[0],lang)}</h3><p>{text(s[1],lang)}</p></div></article>' for i,s in enumerate(p['sections']))
    tabs=''.join(table_html(tb,lang) for tb in p['tables'])
    extras=extra_tables(p)
    fallback=''.join(table_html(tb,lang) for tb in extras)
    all_data= f'<details><summary>{choose(lang,"탐색기의 전체 원문 데이터 보기","View all source data used by the explorer")}</summary>{fallback}</details>' if extras else ''
    related=''
    for other in p['related']:
        target=next(x for x in PROJECTS if x['slug']==other)
        related+=f'<a href="../../{other}/{lang}/index.html"><strong>{E(target["name"])} ↗</strong><span>{text(target["question"],lang)}</span></a>'
    markup=f'''<main id="main" class="wrap"><section class="hero"><div class="eyebrow">{E(p['name'])} &nbsp; / &nbsp; {text(p['venue'],lang)}</div><h1>{text(p['title'],lang)}</h1><p class="subtitle">{text(p['subtitle'],lang)}</p><div class="authors">{authors}</div><p class="affiliation">{text(p['affiliation'],lang)}</p><p class="author-note">{text(p['author_note'],lang)}</p><div class="links">{link_html}</div></section><p class="lead">{text(p['question'],lang)}</p><div class="metrics">{metrics}</div><p class="note">{text(p['metric_note'],lang)}</p><section class="overview" aria-label="{choose(lang,'방법 살펴보기','Method walk-through')}"><div class="section-top"><span class="eyebrow">{choose(lang,'방법 살펴보기','Explore the method')}</span><span class="counter" id="step-counter">01 / 04</span></div><div class="step-grid" role="group" aria-label="{choose(lang,'설명할 단계 선택','Choose a stage')}">{steps}</div><p class="step-description" id="step-description" aria-live="polite">{text(p['steps'][0][1],lang)}</p><p class="source">{text(p['step_source'],lang)}</p><noscript><div class="noscript">{choose(lang,'상호작용은 JavaScript가 필요합니다. 아래 방법 및 표에서 연구 내용을 읽을 수 있습니다.','Interactions require JavaScript. The method and full result tables remain readable below.')}</div></noscript></section><nav class="section-nav" aria-label="{choose(lang,'페이지 목차','On this page')}">{nav}</nav><section class="section" id="abstract"><h2>{l['abstract']}</h2><p class="abstract">{text(p['summary'],lang)}</p></section><section class="section" id="method"><h2>{l['method']}</h2>{stories}</section><section class="section" id="results"><div class="eyebrow">{choose(lang,'측정값을 직접 살펴보세요','Inspect the reported measurements')}</div><h2>{l['results']}</h2><p>{text(p['explorer_intro'],lang)}</p><div class="explorer js-only"><div class="explorer-head"><h3>{choose(lang,'결과 탐색기','Results explorer')}</h3><p>{choose(lang,'원문 실험값 기반 · 실제 모델 추론 아님','Reported experiment values · not live model inference')}</p></div><div class="explorer-body" id="interactive-body"></div></div>{all_data}{tabs}</section>{media_html(p,lang)}<section class="section" id="limits"><h2>{l['limits']}</h2><div class="caveat">{text(p['limitations'],lang)}</div></section><section class="section" id="citation"><div class="citation-head"><h2>{choose(lang,'논문 정보와 인용','Paper details & citation')}</h2><button type="button" class="copy" id="copy-citation">{choose(lang,'BibTeX 복사','Copy BibTeX')}</button></div><p class="formal-title">{E(p['formal_title'])}</p><p class="source">{text(p['source'],lang)}</p><pre id="bibtex">{E(p['bibtex'])}</pre><div class="copy-status" id="copy-status" aria-live="polite"></div><p class="note">{choose(lang,'확인되지 않은 DOI·권호·페이지 번호는 인용 정보에 넣지 않았습니다.','Unverified DOI, volume and page identifiers are omitted from this citation.')}</p></section><section class="section"><h2>{choose(lang,'함께 살펴볼 연구','Related research')}</h2><div class="related">{related}</div></section></main>{footer(lang)}'''
    return shell(lang,p['name']+' — '+local(p['title'],lang),local(p['summary'],lang),markup,p['slug'],p['category'],p)

def index(lang):
    concepts={'endcache':('x₀ ≠ ε',bi('재사용 공간의 선택','Choose the reuse space')),'velocity-reuse':('10 → 1',bi('같은 관측, 적은 호출','Same observation, fewer calls')),'star':('t̂ → p̂, ĉ',bi('시간에서 공간과 유형으로','Time, then location and type')),'navila-patch':('38 / 384',bi('한 변의 비율 ≠ 면적 비율','Side ratio ≠ area ratio')),'lift3d-film':('γ ⊙ H + β',bi('언어로 조정하는 3D 특징','Language-conditioned 3D features')),'act-cbam':('C → S',bi('채널 다음 공간 어텐션','Channel, then spatial attention'))}
    cards=''
    for i,p in enumerate(PROJECTS,1):
        concept,small=concepts[p['slug']]
        search=(p['name']+' '+p['title']['ko']+' '+p['title']['en']+' '+' '.join(p['tags'])).lower()
        href=f'../{p["slug"]}/{lang}/index.html'
        tags=''.join(f'<span class="tag">{E(t)}</span>' for t in p['tags'])
        cards+=f'''<article class="card" data-category="{p['category']}" data-search="{E(search,quote=True)}"><div class="card-visual" aria-hidden="true"><div><div class="card-no">0{i} / 06</div><div class="card-glyph">{E(concept)}</div><div class="card-mini">{text(small,lang)}</div></div><div class="micro-bars"><i style="width:100%"></i><i style="width:68%"></i><i style="width:38%"></i></div></div><div class="card-body"><div class="eyebrow">{text(p['venue'],lang)}</div><h2><a href="{href}">{E(p['name'])}</a></h2><p class="card-title">{text(p['question'],lang)}</p><div class="tags">{tags}</div><a class="card-link" href="{href}"><span>{choose(lang,'프로젝트 살펴보기','Explore the project')}</span><span aria-hidden="true">↗</span></a></div></article>'''
    filters=''.join(f'<button type="button" class="filter" data-filter="{key}" aria-pressed="{str(key=="all").lower()}">{name}</button>' for key,name in [('all',choose(lang,'전체','All')),('efficiency',choose(lang,'추론 효율화','Efficiency')),('perception',choose(lang,'상황 이해','Perception')),('robustness',choose(lang,'강건성','Robustness')),('control',choose(lang,'행동 모델','Control'))])
    markup=f'''<main id="main" class="wrap"><section class="index-hero"><div class="eyebrow">{choose(lang,'선택된 연구 · 2024—2026','Selected research · 2024—2026')}</div><h1>Learning That<br><mark>Moves</mark> Us.</h1><p class="tagline">{choose(lang,'배움이 움직임이 되고, 일상이 되도록.','From learning to movement. From movement to everyday life.')}</p><p class="index-description">{choose(lang,'관측을 이해하고, 행동을 개선하고, 실행의 효율과 강건성을 검증합니다. 제1저자·공동 제1저자 논문 6편의 문제의식과 방법, 실험 결과를 직접 살펴보세요.','Understanding observations, improving actions, and evaluating efficiency and robustness. Explore the questions, methods and results of six first- and co-first-authored papers.')}</p></section><div class="index-divider"><strong>{choose(lang,'연구 프로젝트','Research projects')}</strong><span id="result-count" aria-live="polite">{choose(lang,'6편의 논문','6 papers')}</span></div><div class="index-controls js-only"><div class="filters" role="group" aria-label="{choose(lang,'연구 분야','Research category')}">{filters}</div><label for="project-search" class="search-label"><input class="search-field" id="project-search" type="search" placeholder="{choose(lang,'논문·키워드 검색','Search papers or keywords')}" aria-label="{choose(lang,'논문·키워드 검색','Search papers or keywords')}"></label></div><div class="cards">{cards}</div><p id="empty-results" class="empty" hidden>{choose(lang,'검색 조건에 맞는 논문이 없습니다.','No papers match your search.')}</p><section class="section"><p class="note">{choose(lang,'수치는 각 논문의 실험 조건과 함께 제시합니다. 설명용 상호작용은 실제 모델 출력이나 로봇 영상과 구분됩니다.','Measurements are shown with the corresponding experimental conditions. Explanatory interactions are not presented as model outputs or robot videos.')}</p><details><summary>{choose(lang,'페이지 구성 참고','Page-design references')}</summary><p class="note">{choose(lang,'Nerfies의 탐색형 설명, OpenVLA의 연구 소개 구조, OpenVLA-OFT의 성능·효율 비교, Diffusion Policy의 방법 설명을 참고했습니다. 이 사이트의 코드는 별도로 작성했으며 다른 연구의 영상이나 결과를 가져오지 않았습니다.','The design is informed by Nerfies’ interactive explanations, OpenVLA’s research narrative, OpenVLA-OFT’s success/efficiency comparisons and Diffusion Policy’s method presentation. Code is independently written; no other project’s experimental media or results are reused.')}</p><p class="note"><a href="https://nerfies.github.io/">Nerfies</a> · <a href="https://openvla.github.io/">OpenVLA</a> · <a href="https://openvla-oft.github.io/">OpenVLA-OFT</a> · <a href="https://diffusion-policy.cs.columbia.edu/">Diffusion Policy</a></p></details></section></main>{footer(lang)}'''
    return shell(lang,choose(lang,'연구 프로젝트','Research projects'),choose(lang,'김지원의 제1저자·공동 제1저자 연구 프로젝트 6편','Six first- and co-first-authored research projects by Jiwon Kim'),markup)

def landing():
    return '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>연구 프로젝트 · Jiwon Kim</title></head><body><p><a href="ko/index.html">한국어</a> · <a href="en/index.html">English</a></p><script>(()=>{let l='ko';try{if(localStorage.getItem('research-language')==='en')l='en';}catch(_){}location.replace(l+'/index.html'+location.hash);})();</script></body></html>'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'projects')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    assets=out/'assets';assets.mkdir(exist_ok=True)
    for name in ['site.css','site.js']:shutil.copyfile(HERE/name,assets/name)
    (assets/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#22283a"/><text x="32" y="41" text-anchor="middle" font-family="sans-serif" font-size="25" fill="white">JK</text></svg>',encoding='utf-8')
    (out/'index.html').write_text(landing(),encoding='utf-8')
    for lang in ['ko','en']:
        (out/lang).mkdir(exist_ok=True);(out/lang/'index.html').write_text(index(lang),encoding='utf-8')
    for p in PROJECTS:
        folder=out/p['slug'];folder.mkdir(exist_ok=True)
        (folder/'index.html').write_text(landing(),encoding='utf-8')
        for lang in ['ko','en']:
            (folder/lang).mkdir(exist_ok=True)
            (folder/lang/'index.html').write_text(page(p,lang),encoding='utf-8')
            buf=io.StringIO();writer=csv.writer(buf)
            writer.writerow([local(p['title'],lang)]);writer.writerow([local(p['source'],lang)])
            for tb in extra_tables(p)+p['tables']:
                writer.writerow([]);writer.writerow([local(tb['title'],lang)]);writer.writerow([local(tb['source'],lang)])
                writer.writerow(local(tb['headers'],lang))
                writer.writerows([[local(v,lang) if v is not None else 'NA' for v in row] for row in tb['rows']])
            (folder/f'data-{lang}.csv').write_text(buf.getvalue(),encoding='utf-8-sig')
    # 색인기는 본문이 사전 렌더링된 언어별 URL을 직접 읽을 수 있습니다.
    urls=[f'{BASE}/{l}/' for l in ['ko','en']]+[f'{BASE}/{p["slug"]}/{l}/' for p in PROJECTS for l in ['ko','en']]
    (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc></url>' for u in urls)+'</urlset>',encoding='utf-8')
    print(f'생성 완료: 논문 6편 × 한·영 2종, 목록 2종 → {out}')

if __name__=='__main__':main()
