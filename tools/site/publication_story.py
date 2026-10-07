#!/usr/bin/env python3
"""Paper-grounded presentation pass. No source PDFs, fonts, or new result values are published."""
from __future__ import annotations
import argparse, base64, bz2, copy, hashlib, html, json, re
from pathlib import Path
from publication_story_copy import D as STORIES
HERE = Path(__file__).resolve().parent
VERSION = 'research-story-v1'

def esc(value):
    return html.escape(str(value), quote=True)

def local(value, lang):
    return value.get(lang, '') if isinstance(value, dict) else value

def normalized_source(source):
    """Use explicit Table numbers; keep the experiment name with its source."""
    value = local(source, 'en')
    value = re.sub(r'^(?:IEIE\s+)?Tables?\s+([\d,\s–-]+)', lambda m: ', '.join('Table '+str(n) for n in table_numbers(m[1])), value)
    for suffix in (' · std of the average not reported', ' · arrows indicate better navigation', ' · trainable parameters, not total model size', ' · T: temporal, S: spatial, C: type, ACCS: unified', ' · T/S/C in names denote temporal/spatial/type adapters'):
        value = value.replace(suffix, '')
    value = value.replace(' · approximately 60 Diffusion Policy checkpoints', ' (Diffusion Policy · ~60 checkpoints)')
    return {'ko': value, 'en': value}

def table_numbers(text):
    nums=[]
    for token in text.split(','):
        token=token.strip()
        match=re.fullmatch(r'(\d+)\s*[–-]\s*(\d+)',token)
        if match: nums.extend(range(int(match[1]),int(match[2])+1))
        elif token: nums.append(int(token))
    return nums

def apply_story_copy(papers):
    """Shared expected text for generation and regression checks; numerical values are untouched."""
    for p in papers:
        story=STORIES[p['slug']]
        p['abstract']={lang:' '.join(local(b['body'],lang) for b in story['problem']) for lang in ('ko','en')}
        p['sections']=[[b['title'],b['body']] for b in story['method']]
        p['figure']=story['caption']
        p['intro']=story['results_intro']
        p['metric_sources']=story['metric_refs']
        for s in [*p.get('cache',[]),*p.get('studies',[])]:s['source']=normalized_source(s['source'])
        if p['slug']=='endcache':
            p['studies'][0]['title']={'ko':'Diffusion Policy: endpoint vs. noise','en':'Diffusion Policy: endpoint vs. noise'}
        p['story_version']=VERSION
    return papers

def numerical_snapshot(p):
    return {'metrics':[v for v,_ in p['metrics']], 'cache':[(m['name'],m['N'],m['rows']) for m in p.get('cache',[])], 'studies':[s['rows'] for s in p['studies']]}

def render_blocks(blocks,lang,formulas=None):
    parts=[]
    for i, b in enumerate(blocks):
        equation=(formulas or {}).get(str(i),(formulas or {}).get(i,''))
        parts.append('<div class="story-block"><h3>'+esc(local(b['title'],lang))+'</h3><p>'+esc(local(b['body'],lang))+'</p>'+(('<div class="story-equation" role="math">'+equation+'</div>') if equation else '')+'<small class="story-source">'+esc(b['ref'])+'</small></div>')
    return ''.join(parts)

def replace_once(page,pattern,replacement,label):
    page,n=re.subn(pattern,lambda m:replacement(m) if callable(replacement) else replacement,page,count=1,flags=re.S)
    if n!=1:raise ValueError('Missing publication anchor: '+label)
    return page

def refine_explorer(site):
    path=site/'projects/assets/site.js'
    js=path.read_text(encoding='utf-8')
    if '// '+VERSION in js:return
    edits={
      '원문 실험값 기반 · 실제 모델 추론 아님':'원문 실험값 기반 시각화',
      'Reported experimental values · not live model inference':'Visualization of reported experimental results',
      ' 호출 수 감소와 시간 가속은 다릅니다. 스케줄은 알고리즘의 호출 위치를 설명하며 로봇 동작 영상이 아닙니다.':'',
      ' Call-count and time speedup are distinct. The schedule explains calls, not robot motion.':'',
      '같은 예산에서 무엇을 재사용할까?':'Diffusion Policy: endpoint vs. noise',
      'What should be reused at the same budget?':'Diffusion Policy: endpoint vs. noise',
      "t('모델 호출 수 · 계산값','Calls · calculated')":"t('AG forward passes','AG forward passes')",
      '성능 저하를 별도의 공격 성공률로 표시하지 않습니다. 패치 크기·노출 조건은 각 표의 독립 실험입니다.':'',
      'Degradation is not presented as a separate attack success rate. Patch size and exposure are independent studies.':'',
    }
    for old,new in edits.items():
        if old not in js:raise ValueError('Explorer wording changed: '+old)
        js=js.replace(old,new)
    path.write_text('// '+VERSION+'\n'+js,encoding='utf-8')

def refine(site):
    site=Path(site)
    if not (site/'projects/endcache/ko/index.html').is_file():raise ValueError('Not a built portfolio')
    refine_explorer(site)
    svg=bz2.decompress(base64.b85decode((HERE/'endcache_figure2.svg.b85').read_text().strip())).decode()
    if '<text' in svg or '<image' in svg or '<script' in svg or '@font' in svg:raise ValueError('Figure must contain vector paths only')
    fig_name='endcache-figure2-'+hashlib.sha256(svg.encode()).hexdigest()[:12]+'.svg'
    (site/'projects/assets'/fig_name).write_text(svg,encoding='utf-8')
    css=(HERE/'publication_story.css').read_text(encoding='utf-8')
    css_name='publication-story-'+hashlib.sha256(css.encode()).hexdigest()[:12]+'.css'
    (site/'projects/assets'/css_name).write_text(css,encoding='utf-8')
    report=[]
    for path in site.rglob('*.html'):
        page=path.read_text(encoding='utf-8')
        rel=path.relative_to(site).as_posix()
        if 'endcache.webp' in page:page=page.replace('endcache.webp',fig_name)
        if rel.startswith('projects/'):
            page=re.sub(r'(src="(?:\.\./)*assets/site\.js)(?:\?[^"<>]*)?',r'\1?v='+VERSION,page)
        match=re.search(r'<script type="application/json" id="paper-data">(.*?)</script>',page,re.S)
        if match and rel.startswith('projects/'):
            p=json.loads(match[1]);slug=p['slug'];lang='en' if '/en/' in rel else 'ko';
            if slug=='star':continue
            story=STORIES[slug]
            if 'data-research-story="'+VERSION+'"' in page:
                path.write_text(page,encoding='utf-8');continue
            before=numerical_snapshot(p);original=copy.deepcopy(p);apply_story_copy([p]);assert numerical_snapshot(p)==before
            caption=esc(local(story['caption'],lang))
            page=replace_once(page,r'(<figcaption>).*?(</figcaption>)',lambda m:m[1]+caption+' <span class="zoom-label">⤢ '+('클릭하여 확대' if lang=='ko' else 'Click to enlarge')+'</span>'+m[2],'caption')
            page=replace_once(page,r'(<dialog id="figure-dialog">.*?<p>).*?(</p>)',lambda m:m[1]+caption+m[2],'zoom caption')
            page=page.replace(esc(local(original['figure'],lang)),caption)
            page=re.sub(r'<meta (?:name="description"|property="og:description") content="[^"]*">',lambda m:re.sub(r'content="[^"]*"','content="'+esc(local(story['problem'][0]['body'],lang))+'"',m[0]),page)
            metrics=''.join('<div><strong>'+esc(v)+'</strong><span>'+esc(local(label,lang))+'</span><small class="metric-source">'+esc(ref)+'</small></div>' for (v,label),ref in zip(p['metrics'],story['metric_refs']))
            page=replace_once(page,r'<div class="metrics">.*?</div></div>','<div class="metrics">'+metrics+'</div>','metric cards')
            page=page.replace('<p class="note">'+esc(local(original['metricnote'],lang))+'</p>','')
            overview='<section id="overview"><h2>'+('문제 정의' if lang=='ko' else 'Problem formulation')+'</h2><div class="research-story">'+render_blocks(story['problem'],lang)+'</div></section>'
            page=replace_once(page,r'<section id="overview">.*?</section>',overview,'overview')
            method='<section id="method"><h2>'+('EndCache 설계' if slug=='endcache' and lang=='ko' else 'EndCache protocol' if slug=='endcache' else '설계 선택과 방법' if lang=='ko' else 'Design choices and method')+'</h2><div class="method-copy">'+render_blocks(story['method'],lang)+'</div></section>'
            page=replace_once(page,r'<section id="method">.*?</section>',method,'method')
            if story.get('analysis'):
                analysis='<section id="analysis"><h2>'+('분석' if lang=='ko' else 'Analysis')+'</h2>'+render_blocks(story['analysis'],lang,story.get('formulas'))+'</section>'
                page=page.replace('<section id="method">',analysis+'<section id="method">',1)
            page=replace_once(page,r'(<section id="results"><h2>.*?</h2>)<p>.*?</p>',lambda m:m[1]+'<p class="results-intro">'+esc(local(story['results_intro'],lang))+'</p>','results intro')
            if story.get('evidence'):
                evidence='<div class="results-reasoning">'+render_blocks(story['evidence'],lang)+'</div>'
                page=page.replace('<div id="explorer"',evidence+'<div id="explorer"',1)
            for old,new in zip([*original.get('cache',[]),*original['studies']],[*p.get('cache',[]),*p['studies']]):
                page=page.replace(esc(local(old['source'],lang)),esc(local(new['source'],lang)))
                if 'title' in old and 'title' in new:
                    page=page.replace('<h3>'+esc(local(old['title'],lang))+'</h3>','<h3>'+esc(local(new['title'],lang))+'</h3>')
            for text in ['—: 해당 조건의 결과가 원문에 보고되지 않음. pp: 퍼센트포인트.','—: result not reported for that condition. pp: percentage points.']:
                page=page.replace('<p class="note">'+text+'</p>','')
            payload=json.dumps(p,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
            page=replace_once(page,r'(<script type="application/json" id="paper-data">).*?(</script>)',lambda m:m[1]+payload+m[2],'paper data')
            page=page.replace('<main id="main"','<main data-research-story="'+VERSION+'" id="main"',1)
            page=page.replace('</head>','<link rel="stylesheet" href="/projects/assets/'+css_name+'"></head>',1)
            report.append({'slug':slug,'language':lang,'numbers_unchanged':True,'analysis_before_method':bool(story.get('analysis'))})
        path.write_text(page,encoding='utf-8')
    if len(report)!=10:raise ValueError('Expected ten updated paper pages: '+str(len(report)))
    print(json.dumps({'paper_story_pages':report,'vector_figure':fig_name},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--site',type=Path,required=True)
    refine(ap.parse_args().site)
