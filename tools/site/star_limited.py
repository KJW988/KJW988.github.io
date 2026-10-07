#!/usr/bin/env python3
"""Limit STAR to workshop metadata only in the public GitHub Pages artifact.

This removes published details and rendered figures; it does NOT erase past Git commits,
external mirrors, or third-party caches. Keep source-history hardening separate.
"""
from pathlib import Path
import argparse, html, json, re

VERSION = "star-public-header-v1"
WORKSHOP = "https://www.autopilot-cvpr.net/"
STAR_TITLE = "STAR: Stage-wise Traffic Accident Detection via Optical-Flow-Guided Reasoning"

def one(source, pattern, substitution, label):
    out, count = re.subn(pattern, substitution, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError("Missing " + label)
    return out

def detail(page, lang):
    title = "↗ AUTOPILOT Workshop 2026"
    source = page.read_text(encoding="utf-8")
    main = re.search(r'<main\b[^>]*>.*?</main>', source, re.S)
    if not main:
        raise ValueError("Missing detailed-page main: " + str(page))
    hero = re.search(r'<section\b[^>]*class="hero"[^>]*>.*?</section>', main.group(), re.S)
    if not hero or STAR_TITLE not in hero.group():
        raise ValueError("Missing STAR hero")
    header = hero.group()
    anchor = '<a class="pill primary" href="' + WORKSHOP + '" target="_blank" rel="noopener noreferrer">' + title + "</a>"
    header = one(header, r'<div class="links">.*?</div>', '<div class="links">' + anchor + '</div>', "hero action")
    head = ('<main id="main" class="wrap" data-star-public="' + VERSION + '">'
            + header + "</main>")
    source = source[:main.start()] + head + source[main.end():]
    source = re.sub(r'<dialog id="figure-dialog">.*?</dialog>', '', source, flags=re.S)
    source = re.sub(r'<script type="application/json" id="paper-data">.*?</script>', '', source, flags=re.S)
    description = ("STAR · AUTOPILOT Workshop @ CVPR 2026 · Non-archival" if lang=="en" else
                   "STAR · AUTOPILOT Workshop @ CVPR 2026 · Non-archival")
    source = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*(">)',
                    lambda m:m[1]+html.escape(description,quote=True)+m[2],source)
    source = re.sub(r'<meta property="og:image"[^>]*>', '', source)
    # Avoid a stale preview exposing the former overview.
    source = source.replace('STAR / AUTOPILOT', 'STAR / AUTOPILOT')
    page.write_text(source,encoding="utf-8")
    forbidden = ('paper-data','id="results"','id="method"','id="analysis"',
                 'id="overview"','class="paper-figure"','star-overview',
                 'id="figure-dialog"','data-publication-layout=','data-research-story=')
    for word in forbidden:
        if word in source:
            raise ValueError("Published STAR detail remains (" + word + ")")
    if WORKSHOP not in source or not re.search(r'Non-archival',source,re.I):
        raise ValueError("Missing workshop badge or link")
    return str(page)

def listing(page, lang):
    source = page.read_text(encoding="utf-8")
    article = re.search(r'<article\b[^>]*class="card"[^>]*>.*?</article>', source, re.S)
    # Locate exactly the STAR publication card, not necessarily the first card.
    candidates = [m for m in re.finditer(r'<article\b[^>]*class="card"[^>]*>.*?</article>',source,re.S)
                  if ('../star/'+lang+'/index.html') in m.group()]
    if len(candidates)!=1:
        raise ValueError("Expected exactly one STAR card")
    m = candidates[0]
    item = m.group()
    fallback = ('STAR · CVPR 2026 · Non-archival workshop presentation'
                if lang=="en" else 'STAR · CVPR 2026 · Non-archival 워크숍 발표')
    item = one(item, r'<div class="paper-summary">.*?</div>',
               '<div class="paper-summary"><p class="summary-question">'+fallback+'</p></div>',
               "STAR summary")
    item = one(item, r'(<a class="card-cover"[^>]*>).*?(</a>)',
               lambda z:z[1]+'<span class="star-archive-cover" aria-hidden="true">STAR<small>CVPR 2026 · Non-archival</small></span>'+z[2],
               "STAR thumbnail")
    # Remove discoverable method-specific tag labels from the STAR card while retaining
    # a broad video-understanding keyword, and keep the venue + official paper title.
    item = re.sub(r'data-search="[^"]*"', 'data-search="star cvpr 2026 non-archival workshop"', item, count=1)
    item = one(item, r'<div class="tags">.*?</div>',
               '<div class="tags"><span>VLM</span><span>Video Understanding</span><span>Non-archival</span></div>',
               "STAR tags")
    source = source[:m.start()]+item+source[m.end():]
    css = (".star-archive-cover{width:100%;height:100%;min-height:160px;display:flex;"
           "flex-direction:column;align-items:center;justify-content:center;gap:9px;"
           "background:#f3f6fa;color:#252c40;font-size:38px;font-weight:800;letter-spacing:.04em}"
           ".star-archive-cover small{color:#68758d;font-size:12px;font-weight:600;"
           "letter-spacing:.025em}")
    source = source.replace("</head>",'<style id="star-archive-cover-css">'+css+"</style></head>",1)
    page.write_text(source,encoding="utf-8")
    if 'star-overview' in item or 'Optical flow' in item or 'LoRA' in item:
        raise ValueError("STAR overview exposed on listing")
    return str(page)

def limit(site):
    site = Path(site)
    report = {'version':VERSION,'detail_pages':[],'listing_pages':[],'removed_public_files':[]}
    for lang in ("ko","en"):
        report['detail_pages'].append(detail(site/'projects/star'/lang/'index.html',lang))
        report['listing_pages'].append(listing(site/'projects'/lang/'index.html',lang))
    # Other publication pages may link to STAR; keep the relationship but
    # replace their formerly method-specific teaser with venue-only metadata.
    for path in site.rglob('*.html'):
        if path.parent.name not in ("ko","en") or path.parent.parent.name=="star":
            continue
        source=path.read_text(encoding="utf-8")
        source,n=re.subn(
            r'(<a class="related" href="[^"]*/star/(?:ko|en)/index.html"><strong>.*?</strong>)<span>.*?</span>(</a>)',
            lambda m:m[1]+'<span>AUTOPILOT Workshop @ CVPR 2026 · Non-archival</span>'+m[2],
            source,flags=re.S
        )
        if n:path.write_text(source,encoding="utf-8")
    for root in [site/'projects/assets',site/'projects/star']:
        for path in list(root.rglob('*')):
            if not path.is_file():continue
            if (root.name=='assets' and
                (path.name=="star.webp" or path.name.startswith("star-overview"))) or (
                root.name=='star' and path.suffix.lower() in ('.csv','.pdf','.json','.svg','.webp','.png','.jpeg','.jpg')):
                report['removed_public_files'].append(path.relative_to(site).as_posix())
                path.unlink()
    for manifest_name in ('sources.json','completion-status.json'):
        manifest=site/'projects'/manifest_name
        if manifest.exists():
            obj=json.loads(manifest.read_text(encoding="utf-8"))
            if manifest_name=='sources.json':
                obj.get('figures_git_sha1',{}).pop('star',None)
                obj.get('paper_links',{}).pop('star',None)
            else:
                obj.get('media',{}).pop('star-overview.svg',None)
                # Avoid publishing a metadata record that describes the removed overview.
                obj['missing_media']=[n for n in obj.get('missing_media',[]) if n!='star-overview.svg']
            manifest.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    # Do not allow the retired overview to survive as a direct public URL.
    for p in (site/'projects/assets').glob('star*'):
        if p.is_file() and p.name != "star-unrelated":raise ValueError("STAR asset still published: "+str(p))
    (site/'projects/star/publication-notice.json').write_text(
        json.dumps({'version':VERSION,'visibility':'metadata-only','workshop':WORKSHOP,
                    'raw-paper':False,'overview':False,'results':False,
                    'warning':'Previous public Git history and external caches require separate review.'},
                   ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,required=True)
    limit(parser.parse_args().site)
