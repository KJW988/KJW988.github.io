#!/usr/bin/env python3
"""Shared navigation, editorial cleanup and source links on the public artifact only."""
from __future__ import annotations
import json
import re
from html import escape
from pathlib import Path

SEMINAR_TITLE = '연구실 세미나 발표자료 아카이브'
# Original-paper landing pages: never the author's presentation source files.
SOURCES = {
    'bac': {'title':'Block-wise Adaptive Caching for Accelerating Diffusion Policy', 'paper':'https://arxiv.org/abs/2506.13456', 'project':'https://block-wise-adaptive-caching.github.io/'},
    'ddt': {'title':'DDT: Decoupled Diffusion Transformer', 'paper':'https://arxiv.org/abs/2504.05741'},
    'dualvln': {'title':'Ground Slow, Move Fast: A Dual-System Foundation Model for Generalizable Vision-and-Language Navigation', 'paper':'https://arxiv.org/abs/2512.08186', 'project':'https://dualvln.github.io/'},
    'visionzip': {'title':'VisionZip: Longer is Better but Not Necessary in Vision Language Models', 'paper':'https://arxiv.org/abs/2412.04467'},
    'r-tpt': {'title':'R-TPT: Improving Adversarial Robustness of Vision-Language Models through Test-Time Prompt Tuning', 'paper':'https://arxiv.org/abs/2504.11195'},
    'clip-rt': {'title':'CLIP-RT: Learning Language-Conditioned Robotic Policies from Natural Language Supervision', 'paper':'https://arxiv.org/abs/2411.00508', 'project':'https://clip-rt.github.io/'},
    'moka': {'title':'MOKA: Open-World Robotic Manipulation through Mark-Based Visual Prompting', 'paper':'https://arxiv.org/abs/2403.03174', 'project':'https://moka-manipulation.github.io/'},
    'active-tta-vln': {'title':'Active Test-time Vision-Language Navigation', 'paper':'https://arxiv.org/abs/2506.06630'},
    'vla-cache': {'title':'VLA-Cache: Efficient Vision-Language-Action Manipulation via Adaptive Token Caching', 'paper':'https://arxiv.org/abs/2502.02175', 'project':'https://vla-cache.github.io/'},
    'image-as-imu': {'title':'Image as an IMU: Estimating Camera Motion from a Single Motion-Blurred Image', 'paper':'https://arxiv.org/abs/2503.17358', 'project':'https://jerredchen.github.io/image-as-imu/'},
}

CSS = r'''
/* One navigation system across the homepage, Publication and seminar archive. */
.sitewide-header{position:sticky;top:0;z-index:60;background:rgba(255,255,255,.96);border-bottom:1px solid #e7eaf0;backdrop-filter:blur(12px)}
.sitewide-header .sitewide-nav{box-sizing:border-box;width:calc(100% - 64px);max-width:1120px;margin:0 auto;min-height:74px;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:30px;padding:0;font-family:inherit}
.sitewide-header a{color:#536078;text-decoration:none;border:0;box-shadow:none;background:none;line-height:1.5;letter-spacing:0}
.sitewide-header .sitewide-brand{font-size:17px;font-weight:750;color:#242a3d;white-space:nowrap;min-height:44px;display:inline-flex;align-items:center}
.sitewide-brand .brand-dot{color:#3862a7;margin-left:2px}
.sitewide-header .nav-links{display:flex;align-items:center;justify-content:flex-start;gap:26px;margin:0;padding:0}
.sitewide-header .nav-links a{font-size:13px;min-height:44px;display:inline-flex;align-items:center;white-space:nowrap}
.sitewide-header .nav-links a[aria-current=page]{color:#242a3d;font-weight:700}
.sitewide-header a:hover{color:#244c93;text-decoration:underline;text-underline-offset:5px}
.sitewide-header a:focus-visible{outline:2px solid #4b76bf;outline-offset:4px;border-radius:2px}
.sitewide-header .languages{border:0;border-radius:0;background:none;box-shadow:none;display:flex;gap:10px;align-items:center;margin:0;padding:0;white-space:nowrap}
.sitewide-header .languages a{display:inline-flex;align-items:center;min-height:44px;font-size:12px;padding:0;border:0;border-radius:0;font-weight:400;background:none}
.sitewide-header .languages a[aria-current=page]{color:#242a3d;font-weight:700}
.sitewide-header .language-divider{color:#a6adbc;font-size:12px}
.sitewide-header .archive-language{font-size:11px;color:#798398;white-space:nowrap}
html{scroll-padding-top:92px}
section[id],#player{scroll-margin-top:96px}
/* Keep the lettering still; only its highlighter accelerates and settles. */
mark.moves-mark{position:relative;isolation:isolate;display:inline-block;background:none!important;color:inherit;padding:0 .045em;white-space:nowrap;vertical-align:baseline}
mark.moves-mark::before{content:"";position:absolute;z-index:-1;left:-.015em;right:-.035em;top:55%;height:40%;border-radius:.06em;background:#e2ebfd;transform:translateX(0) skewX(-7deg);transform-origin:50% 80%;pointer-events:none}
mark.moves-mark::after{content:"";position:absolute;z-index:-1;width:32%;height:.025em;left:-.04em;bottom:.02em;background:linear-gradient(90deg,transparent,#92b2e9);opacity:0;pointer-events:none}
@keyframes marker-drive{0%{transform:translateX(0) skewX(-7deg)}15%{transform:translateX(-.045em) scaleX(.98) skewX(-4deg)}52%{transform:translateX(.19em) scaleX(1.035) skewX(-13deg)}78%{transform:translateX(-.025em) skewX(-6deg)}100%{transform:translateX(0) skewX(-7deg)}}
@keyframes marker-trail{0%,100%{opacity:0;transform:scaleX(.3)}35%{opacity:.42;transform:translateX(-.09em) scaleX(1.2)}70%{opacity:0;transform:translateX(.05em) scaleX(.5)}}
@media(hover:hover) and (pointer:fine){mark.moves-mark:hover::before{animation:marker-drive .82s cubic-bezier(.22,.7,.28,1) both}mark.moves-mark:hover::after{animation:marker-trail .82s ease-out both}}
mark.moves-mark:focus-visible{outline:2px solid #7b9bc8;outline-offset:5px;border-radius:3px}
mark.moves-mark:focus-visible::before{animation:marker-drive .82s cubic-bezier(.22,.7,.28,1) both}
/* Meaningful Korean word groups and balanced questions, without fixed line heights. */
.index-intro{white-space:pre-line;max-width:960px!important;word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty}
.paper-summary{min-width:0}
.paper-summary .lead,.paper-summary .summary-question{word-break:keep-all;overflow-wrap:break-word;text-wrap:balance}
.paper-summary .summary-points{word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty;padding-left:1.15em;line-height:1.85;margin:10px 0}
.paper-summary .summary-points li{margin:4px 0;padding-left:2px}
.paper-summary .summary-note{margin:12px 0 0!important;font-size:12px!important;color:#748096;line-height:1.75;text-wrap:pretty}
.card-body .summary-question{font-size:14px;line-height:1.8;font-weight:650;color:#242a3d}
.card-body .summary-points{font-size:13px;line-height:1.9}
.hero h1,.card h2.paper-title,.related strong{word-break:keep-all;overflow-wrap:break-word;text-wrap:balance}
.method-copy p,.abstract,.caveat,.prose p,.award-description{word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty}
.section-nav{top:74px}
@media(max-width:580px){.section-nav{top:79px}}
/* Source-paper links follow the selected seminar without opening a document embed. */
.intro h1{word-break:keep-all;text-wrap:balance;font-size:clamp(26px,3.2vw,38px);line-height:1.4}
.seminar-source{display:flex;align-items:center;justify-content:space-between;gap:22px;margin:18px 0 16px;padding:16px 0;border-top:1px solid #e1e6ef;border-bottom:1px solid #e1e6ef}
.seminar-source .source-title{font-size:14px;line-height:1.65;color:#39455c;max-width:730px;margin:0;word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty}
.seminar-source .source-kicker{font-size:10px;letter-spacing:.08em;color:#798398;display:block;margin-bottom:4px}
.seminar-source .source-links{display:flex;gap:16px;flex-shrink:0;flex-wrap:wrap}
.seminar-source .source-links a{font-size:12px;line-height:1.7;color:#344967;white-space:nowrap;text-decoration:underline;text-underline-offset:5px;padding:5px 0}
.seminar-source a:focus-visible{outline:2px solid #557db4;outline-offset:4px}
@media(max-width:760px){.sitewide-header .sitewide-nav{width:calc(100% - 40px);gap:18px}.sitewide-header .nav-links{gap:18px}.sitewide-header .sitewide-brand{font-size:15px}.sitewide-header .nav-links a{font-size:12px}.sitewide-header .languages{gap:8px}.seminar-source{flex-direction:column;align-items:flex-start;gap:8px}.seminar-source .source-title{font-size:13px}}
@media(max-width:580px){.sitewide-header .sitewide-nav{grid-template-columns:1fr auto;min-height:0;row-gap:0;padding:5px 0 4px}.sitewide-header .nav-links{grid-column:1 / -1;grid-row:2;gap:26px}.sitewide-header .languages,.sitewide-header .archive-language{grid-column:2;grid-row:1}.sitewide-header .nav-links a{min-height:34px}.sitewide-header .sitewide-brand{min-height:36px}.sitewide-header .languages a{min-height:36px}.sitewide-header .archive-language{font-size:10px}html{scroll-padding-top:100px}.paper-summary .lead{font-size:18px;line-height:1.75}.card-body .summary-question{font-size:14px}}
@media(prefers-reduced-motion:reduce){mark.moves-mark::before,mark.moves-mark::after{animation:none!important;transition:none!important}}
'''

JS = r'''"use strict";
(() => {
  // Follow the viewer's selected title; its hash uses replaceState on deck changes.
  const panel=document.getElementById("seminar-source");
  const metadata=document.getElementById("seminar-sources");
  const title=document.getElementById("deck-title");
  if(panel&&metadata&&title){
    const sources=JSON.parse(metadata.textContent);
    const decks=window.SEMINAR_DECKS||[];
    const render=()=>{
      const deck=decks.find(d=>d.title===title.textContent.trim());
      const item=deck&&sources[deck.id];
      if(!item){panel.hidden=true;return;}
      panel.hidden=false;panel.dataset.deck=deck.id;
      panel.querySelector('.source-paper-title').textContent=item.title;
      const links=panel.querySelector('.source-links');links.replaceChildren();
      for(const [key,label] of [['paper','논문 원문 ↗'],['project','프로젝트 페이지 ↗']]){
        if(!item[key])continue;
        const a=document.createElement('a');a.href=item[key];a.textContent=label;
        a.target='_blank';a.rel='noopener noreferrer';a.dataset.source=key;links.append(a);
      }
    };
    new MutationObserver(render).observe(title,{childList:true,characterData:true,subtree:true});render();
  }
})();
'''


def header(lang, route):
    seminar=route.startswith('seminars/')
    publication=route.startswith('projects/')
    home='/en/' if lang=='en' else '/'
    target='/projects/'+lang+'/'
    current='seminar' if seminar else 'publication' if publication else 'home'
    def link(href,label,key,cls=''):
        return f'<a class="{cls}" href="{href}"'+(' aria-current="page"' if key==current else '')+'>'+label+'</a>'
    links=link(home,'About me','home','about-nav')+link(target,'Publication','publication','research-nav')+link('/seminars/','Seminars' if lang=='en' else '세미나','seminar','seminars-nav')
    if seminar:
        languages='<span class="archive-language">한국어 발표자료</span>'
    else:
        def language(l,label):
            href='/'+route.replace('/'+lang+'/', '/'+l+'/') if publication else ('/en/' if l=='en' else '/')
            if href.endswith('index.html'):href=href[:-10]
            return f'<a class="language" lang="{l}" hreflang="{l}" href="{href}"'+(' aria-current="page"' if lang==l else '')+'>'+label+'</a>'
        languages='<div class="languages" aria-label="Language">'+language('ko','한국어')+'<span class="language-divider" aria-hidden="true">/</span>'+language('en','English')+'</div>'
    return '<header class="sitewide-header" id="site-header"><nav class="sitewide-nav" aria-label="Main navigation"><a class="sitewide-brand blog-back" href="'+home+'">Jiwon Kim<span class="brand-dot" aria-hidden="true">.</span></a><div class="nav-links">'+links+'</div>'+languages+'</nav></header>'


def source_panel(item, deck_id):
    links=''.join('<a data-source="'+key+'" href="'+escape(item[key],quote=True)+'" target="_blank" rel="noopener noreferrer">'+label+'</a>' for key,label in [('paper','논문 원문 ↗'),('project','프로젝트 페이지 ↗')] if item.get(key))
    return '<section id="seminar-source" class="seminar-source" data-deck="'+deck_id+'" aria-label="발표 논문의 원문과 프로젝트"><p class="source-title"><span class="source-kicker">발표 논문</span><span class="source-paper-title">'+escape(item['title'])+'</span></p><div class="source-links">'+links+'</div></section>'


def polish(site):
    site=Path(site)
    for name,content in [('projects/assets/sitewide.css',CSS),('projects/assets/sitewide.js',JS)]:
        p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')
    for path in site.rglob('*.html'):
        page=path.read_text(encoding='utf-8');rel=path.relative_to(site).as_posix()
        lang='en' if '<html lang="en"' in page else 'ko'
        page=page.replace('연구 출판물','Publication').replace('Research projects','Publication')
        page=page.replace('/ Publications','/ Publication').replace('>Publications<','>Publication<').replace('Publications · Jiwon Kim','Publication · Jiwon Kim')
        if rel.startswith('projects/'):
            page=re.sub(r'<section><details><summary>(?:페이지 구성 참고|Page-design references)</summary>.*?</details></section>','',page,flags=re.S)
            def footer(match):
                body=re.sub(r'<p>.*?</p>','',match.group(2),flags=re.S)
                return match.group(1)+body+match.group(3)
            page=re.sub(r'(<footer\b[^>]*>)(.*?)(</footer>)',footer,page,flags=re.S)
        if '<header' in page:
            page=re.sub(r'<header\b[^>]*>.*?</header>',lambda _:header(lang,rel),page,count=1,flags=re.S)
        page=re.sub(r'<mark>Moves</mark>', '<mark class="moves-mark" tabindex="0">Moves</mark>',page)
        if rel=='seminars/index.html':
            data=(site/'seminars/slides.js').read_text(encoding='utf-8').strip()
            decks=json.loads(data.removeprefix('window.SEMINAR_DECKS=').removesuffix(';'))
            missing=[d['id'] for d in decks if d['id'] not in SOURCES]
            if missing:raise ValueError('Missing original-paper source: '+repr(missing))
            page=re.sub(r'<h1\b[^>]*>.*?</h1>','<h1>'+SEMINAR_TITLE+'</h1>',page,count=1,flags=re.S)
            page=re.sub(r'<p class="description"[^>]*>.*?</p>','',page,count=1,flags=re.S)
            count=sum(len(d['slides']) for d in decks)
            label=f'{len(decks)}개 발표자료 · {count}장' if len(decks)==10 else f'미리보기 {len(decks)}개 · {count}장'
            page=re.sub(r'<p class="sample-note"[^>]*>.*?</p>','<p class="sample-note">'+label+'</p>',page,count=1,flags=re.S)
            page=page.replace('<title>세미나 슬라이드쇼 · Jiwon Kim</title>','<title>'+SEMINAR_TITLE+' · Jiwon Kim</title>')
            page=page.replace('김지원 · 세미나 자료','김지원 · '+SEMINAR_TITLE)
            page=re.sub(r'<meta name="description"[^>]*>','<meta name="description" content="연구실에서 발표한 논문 리뷰 자료와 원문 링크.">',page,count=1)
            if 'id="seminar-source"' not in page:
                first=decks[0]
                page=page.replace('<section id="player"',source_panel(SOURCES[first['id']],first['id'])+'\n<section id="player"',1)
                safe=json.dumps({d['id']:SOURCES[d['id']] for d in decks},ensure_ascii=False).replace('<','\\u003c')
                page=page.replace('</body>','<script type="application/json" id="seminar-sources">'+safe+'</script></body>')
        if '/projects/assets/sitewide.css' not in page:
            page=page.replace('</head>','<link rel="stylesheet" href="/projects/assets/sitewide.css?v=20261001"><script src="/projects/assets/sitewide.js?v=20261001" defer></script></head>',1)
        path.write_text(page,encoding='utf-8')
    print('Shared Publication navigation, Moves highlight, concise summaries and seminar source links applied.')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--site',type=Path,required=True)
    polish(parser.parse_args().site)
