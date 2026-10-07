#!/usr/bin/env python3
"""Final public-only presentation pass: coupled word motion and shorter paper pages."""
from __future__ import annotations
import argparse
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from seminar_labels import refine_seminar_labels

HOME_SLUGS = ('endcache','navila-patch','lift3d-film')
SLUGS = ('endcache','velocity-reuse','star','navila-patch','lift3d-film','act-cbam')
CSS = r'''
/* Shared by About and Publication, including their English pages. */
.moves-pair{position:relative;display:inline-flex;align-items:baseline;gap:.18em;white-space:nowrap;vertical-align:baseline;font:inherit;letter-spacing:inherit;line-height:inherit;color:inherit;isolation:isolate}
.moves-pair>mark.moves-mark{position:relative;display:inline-block;isolation:isolate;vertical-align:baseline;margin:0;padding:0 .03em;background:none!important;color:inherit;font:inherit;font-style:normal!important;letter-spacing:inherit;line-height:inherit;transform:none!important;overflow:visible}
.moves-pair>mark.moves-mark::before{content:"";position:absolute;z-index:-1;inset:auto 0 .065em;height:.32em;border-radius:2px;background:#f0cf55!important;transform:translate3d(var(--marker-x,0px),0,0);clip-path:polygon(var(--marker-lean-right,0px) 0,calc(100% - var(--marker-lean-left,0px)) 0,calc(100% - var(--marker-lean-right,0px)) 100%,var(--marker-lean-left,0px) 100%);animation:none!important;transition:none!important;pointer-events:none}
.moves-pair>mark.moves-mark::after{content:none!important;animation:none!important}
.moves-pair>.moves-us{position:relative;display:inline-block;margin:0;padding:0;font:inherit;font-style:normal;letter-spacing:inherit;line-height:inherit;color:inherit;transform:translate3d(var(--us-x,0px),0,0);animation:none!important;transition:none!important}
/* Translation and the bounded background shear follow the force/impulse model.
 * The word boxes stay upright; only the marker silhouette becomes a parallelogram. */
.moves-pair.is-moving>mark.moves-mark::before,.moves-pair.is-moving>.moves-us{will-change:transform}
.moves-pair.is-moving>mark.moves-mark::before{will-change:transform,clip-path}
.moves-pair>mark.moves-mark:focus-visible{outline:2px solid #bc9221;outline-offset:5px;border-radius:2px}
@media(prefers-reduced-motion:reduce){.moves-pair>mark.moves-mark::before,.moves-pair>.moves-us{animation:none!important;transform:none!important;transition:none!important}.moves-pair>mark.moves-mark::before{clip-path:none!important}}
/* Featured cards reuse the Publication summary verbatim, not a separate short copy. */
.research-copy .paper-summary{margin-top:14px;min-width:0}
.research-copy .summary-question{font-size:14px;font-weight:650;line-height:1.8;color:#242a3d;word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty}
.research-copy .summary-points{margin:10px 0;padding-left:1.15em;font-size:13px;line-height:1.85;color:#505d6b;word-break:keep-all;overflow-wrap:break-word;text-wrap:pretty}
.research-copy .summary-points li{margin:4px 0;padding-left:2px}
.research-copy .summary-note{margin-top:12px!important;font-size:12px!important;line-height:1.75;color:#748096}

'''
JS = Path(__file__).with_name('motion-physics.js').read_text(encoding='utf-8')

class RemovePaperUI(HTMLParser):
    """Drop requested elements; retain all text and script data outside them."""
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(convert_charrefs=False);self.out=[];self.depth=0;self.removed=[]
    def target(self,tag,attrs):
        a=dict(attrs)
        if tag=='section' and a.get('id') in {'limits','citation'}:return a['id']
        if tag=='a' and ('download' in a or a.get('href') in {'#limits','#citation'}):return 'link'
        if tag=='meta' and a.get('name','').startswith('citation_'):return 'citation-meta'
        return None
    def handle_starttag(self,tag,attrs):
        if self.depth:
            if tag not in self.VOID:self.depth+=1
            return
        target=self.target(tag,attrs)
        if target:
            self.removed.append(target)
            if tag not in self.VOID:self.depth=1
        else:self.out.append(self.get_starttag_text())
    def handle_startendtag(self,tag,attrs):
        if not self.depth and not self.target(tag,attrs):self.out.append(self.get_starttag_text())
    def handle_endtag(self,tag):
        if self.depth:
            if tag not in self.VOID:self.depth-=1
        else:self.out.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.depth:self.out.append(data)
    def handle_entityref(self,name):
        if not self.depth:self.out.append('&'+name+';')
    def handle_charref(self,name):
        if not self.depth:self.out.append('&#'+name+';')
    def handle_comment(self,data):
        if not self.depth:self.out.append('<!--'+data+'-->')
    def handle_decl(self,decl):
        if not self.depth:self.out.append('<!'+decl+'>')


def publication_summaries(site:Path,lang:str):
    """Use the generated Publication list as the single source of visible card copy."""
    page=(site/'projects'/lang/'index.html').read_text(encoding='utf-8')
    summaries={}
    for article in re.findall(r'<article\b[^>]*class="card"[^>]*>.*?</article>',page,flags=re.S):
        target=re.search(r'href="\.\./([^/]+)/'+lang+r'/index\.html"',article)
        block=re.search(r'<div class="paper-summary">.*?</div>',article,flags=re.S)
        if target and block:
            if target[1] in summaries:raise ValueError('Duplicate Publication card')
            summaries[target[1]]=block[0]
    if set(summaries)!=set(SLUGS):raise ValueError('Incomplete Publication list: '+lang)
    return summaries


def sync_home_cards(page:str,canonical:dict[str,str],lang:str):
    seen=[]
    def replace(match):
        article=match[0]
        target=re.search(r'href="/projects/([^/]+)/'+lang+r'/',article)
        if not target or target[1] not in HOME_SLUGS:raise ValueError('Unexpected featured paper')
        slug=target[1];seen.append(slug)
        summary=canonical[slug]
        if slug=='endcache':
            # The follow-up note stays on the Publication list and paper page only.
            summary=re.sub(r'<p class="summary-note">.*?</p>','',summary,flags=re.S)
        article=re.sub(r'<div class="paper-summary">.*?</div>','',article,flags=re.S)
        article,n=re.subn(r'(</h3>)\s*(?:<p>.*?</p>)?',lambda m:m[1]+summary,article,count=1,flags=re.S)
        if n!=1:raise ValueError('Featured-card heading not found')
        return article
    page=re.sub(r'<article\b[^>]*class="research-card"[^>]*>.*?</article>',replace,page,flags=re.S)
    if tuple(seen)!=HOME_SLUGS:raise ValueError('Featured paper selection/order changed')
    return page

def refine(site:Path):
    site=Path(site)
    if not site.is_dir():raise ValueError('Built site directory does not exist')
    refine_seminar_labels(site)
    canonical={lang:publication_summaries(site,lang) for lang in ('ko','en')}
    version=hashlib.sha256((CSS+JS).encode()).hexdigest()[:12]
    stem='moves-us-'+version
    assets=site/'projects/assets'
    assets.mkdir(parents=True,exist_ok=True)
    (assets/(stem+'.css')).write_text(CSS,encoding='utf-8')
    (assets/(stem+'.js')).write_text(JS,encoding='utf-8')
    # A critical color rule prevents a legacy theme from flashing blue while CSS loads.
    critical='<style id="moves-critical">.moves-pair>mark.moves-mark{background:none!important}.moves-pair>mark.moves-mark::before{background:#f0cf55!important}</style>'
    injected=critical+f'<link rel="stylesheet" href="/projects/assets/{stem}.css"><script defer src="/projects/assets/{stem}.js"></script>'
    changed_details=0;changed_heroes=0
    for path in site.rglob('*.html'):
        original=page=path.read_text(encoding='utf-8')
        rel=path.relative_to(site).as_posix()
        if rel in {'index.html','en/index.html'}:
            lang='en' if rel.startswith('en/') else 'ko'
            page=sync_home_cards(page,canonical[lang],lang)
        if rel in {f'projects/{s}/{l}/index.html' for s in SLUGS for l in ('ko','en')}:
            parser=RemovePaperUI();parser.feed(page);parser.close()
            if parser.depth:raise ValueError('Unclosed removed section in '+rel)
            if parser.removed.count('limits')!=1 or parser.removed.count('citation')!=1:
                # Re-running this build pass must remain safe.
                if 'id="citation"' in page or 'id="limits"' in page:raise ValueError('Unexpected paper markup: '+rel)
            page=''.join(parser.out);changed_details+=1
        if 'Learning That' in page:
            if 'class="moves-pair"' not in page:
                page,n=re.subn(r'(<mark\b[^>]*>Moves</mark>)\s*Us\.',r'<span class="moves-pair" data-motion-version="spring-contact-v3" data-lean-version="spring-lean-v1">\1 <span class="moves-us">Us.</span></span>',page)
                if n!=1:raise ValueError('Expected one Moves/Us pair in '+rel)
            page=page.replace('data-motion-version="push-pull-v2"','data-motion-version="spring-contact-v3"')
            if 'data-lean-version="spring-lean-v1"' not in page:
                page=page.replace('data-motion-version="spring-contact-v3"','data-motion-version="spring-contact-v3" data-lean-version="spring-lean-v1"')
            # Remove a prior component injection before adding this content-addressed build.
            page=re.sub(r'<style id="moves-critical">.*?</style>','',page,flags=re.S)
            page=re.sub(r'<link\b[^>]*href="/projects/assets/moves-us-[^\"]+\.css"[^>]*>','',page)
            page=re.sub(r'<script\b[^>]*src="/projects/assets/moves-us-[^\"]+\.js"[^>]*>\s*</script>','',page)
            page=page.replace('</head>',injected+'</head>',1);changed_heroes+=1
        if page!=original:path.write_text(page,encoding='utf-8')
    if changed_details!=12 or changed_heroes!=4:
        raise ValueError(f'Expected 12 paper pages and 4 heroes; got {changed_details}, {changed_heroes}')
    print(f'Coupled yellow motion on {changed_heroes} heroes; removed downloads, citation and limitations UI on {changed_details} paper pages; slide/result data unchanged.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',required=True,type=Path)
    refine(p.parse_args().site)
