#!/usr/bin/env python3
"""Table-first publication presentation; numerical/source data are never rewritten."""
from pathlib import Path
import argparse, hashlib, html, json, re

VERSION = 'table-first-v1'
SLUGS = ('endcache', 'velocity-reuse', 'star', 'navila-patch', 'lift3d-film', 'act-cbam')
CACHE = {'endcache', 'velocity-reuse'}
CSS = r'''
/* Counts are a quiet, non-interactive overview, not a second set of filters. */
.publication-breakdown{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));max-width:860px;margin:30px 0 4px;padding:22px 0;border-top:1px solid #e3e7ee;border-bottom:1px solid #e3e7ee;gap:24px}
.publication-breakdown>div{min-width:0;padding-left:24px;border-left:1px solid #e3e7ee}
.publication-breakdown>div:first-child{border-left:0;padding-left:0}
.publication-breakdown dt{font-size:13px;line-height:1.7;color:#5f6c80;word-break:keep-all}
.publication-breakdown dd{margin:6px 0 0;color:#22283a;font-size:32px;font-weight:650;line-height:1.25;font-variant-numeric:tabular-nums}
.publication-breakdown dd small{display:block;margin-top:8px;color:#7a8596;font-size:11px;font-weight:400;line-height:1.65;word-break:keep-all}
[data-publication-layout] .result-tables{margin-top:30px}
[data-publication-layout] .result-tables .table-block{margin:32px 0 40px;border-top:1px solid #e0e5ed;padding-top:22px}
[data-publication-layout] .result-tables h3{margin:0 0 14px;font-size:18px;line-height:1.7;word-break:keep-all}
[data-publication-layout] .table-wrap,[data-publication-layout] .table-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain}
[data-publication-layout] table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
[data-publication-layout] tbody th{font-weight:400}
[data-publication-layout] .dataset-label th{background:#eef2f7;color:#526077;font-weight:600;text-align:left;padding:10px 14px;font-size:12px}
[data-publication-layout] .result-tables .source{text-align:right;margin-top:10px;color:#79849a;font-size:11px;line-height:1.8}
[data-publication-layout] #related{margin-top:60px;padding-top:28px;border-top:1px solid #e0e5ed}
@media(max-width:600px){.publication-breakdown{gap:12px;padding:18px 0;margin-top:24px}.publication-breakdown>div{padding-left:12px}.publication-breakdown dt{font-size:11px}.publication-breakdown dd{font-size:26px}.publication-breakdown dd small{font-size:10px}[data-publication-layout] .result-tables h3{font-size:16px}}
@media(max-width:360px){.publication-breakdown{gap:8px}.publication-breakdown>div{padding-left:8px}.publication-breakdown dd{font-size:24px}}
'''

def text(value, lang):
    return str(value[lang] if isinstance(value, dict) else value)

def esc(value):
    return html.escape(str(value), quote=True)

def once(source, pattern, replacement):
    result, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Expected one element: ' + pattern)
    return result

def number(value, digits=None):
    if value is None:
        return '—'
    if isinstance(value, (int, float)):
        return f'{value:.{digits}f}' if digits is not None else f'{value:g}'
    return esc(value)

def table_block(title, headers, groups, source, digits=None):
    """Groups consist of (optional dataset label, complete rows). No metric selector."""
    body = []
    for group, rows in groups:
        if group:
            body.append(f'<tr class="dataset-label"><th scope="rowgroup" colspan="{len(headers)}">{esc(group)}</th></tr>')
        for row in rows:
            body.append('<tr><th scope="row">' + esc(row[0]) + '</th>' + ''.join(
                '<td>' + number(value, None if digits is None else digits[i]) + '</td>'
                for i, value in enumerate(row[1:])) + '</tr>')
    return ('<article class="table-block"><h3>' + esc(title) + '</h3>'
            '<div class="table-scroll" tabindex="0" role="region" aria-label="' + esc(title) + '">'
            '<table><thead><tr>' + ''.join('<th scope="col">' + esc(h) + '</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'
            '<p class="source">' + esc(source) + '</p></article>')

def static_tables(paper, lang):
    studies = paper['studies']; slug = paper['slug']
    config = '구성' if lang == 'ko' else 'Configuration'
    if slug == 'navila-patch':
        titles = ('패치 생성 방식', '패치 크기', '패치 노출 조건') if lang == 'ko' else ('Patch construction', 'Patch size', 'Patch exposure')
        if len(studies) != 6:
            raise ValueError('Expected the six reported navigation studies')
        blocks = []
        for i, title in enumerate(titles):
            left, right = studies[i], studies[i + 3]
            if left['cols'] != right['cols']:
                raise ValueError('Navigation columns are not aligned')
            groups = [('R2R-CE · Val-Unseen', left['rows']), ('RxR-CE · Val-Unseen', right['rows'])]
            blocks.append(table_block(title, [config] + [text(c, lang) for c in left['cols']],
                                      groups, f'Table {i + 1} · Val-Unseen', [2, 1, 1, 1]))
        return ''.join(blocks)
    if slug == 'act-cbam':
        if len(studies) != 2:
            raise ValueError('Expected success and parameter studies')
        parameters = {r[0]: r[1] for r in studies[1]['rows']}
        if set(parameters) != {r[0] for r in studies[0]['rows']}:
            raise ValueError('Parameter and success configurations differ')
        rows = [r + [parameters[r[0]]] for r in studies[0]['rows']]
        title = '성공률과 학습 가능한 파라미터' if lang == 'ko' else 'Task success and trainable parameters'
        headers = [config, 'Transfer Cube (%) ↑', 'Insertion (%) ↑', 'Trainable params (M) ↓']
        return table_block(title, headers, [(None, rows)], 'Table 1', [0, 0, 2])
    if slug == 'lift3d-film':
        study = studies[0]
        headers = ['과업' if lang == 'ko' else 'Task'] + [text(c, lang) + ' (%) ↑' for c in study['cols']]
        title = '지시문에 따른 과업별 성공률' if lang == 'ko' else 'Per-task success by instruction'
        return table_block(title, headers, [(None, study['rows'])], 'Table 1, Table 2 · Meta-World', [1, 1, 1])
    raise ValueError('Unsupported static table: ' + slug)

def summary(lang):
    # EndCache accepted status is recorded in the author's final portfolio.
    # STAR is an international workshop presentation, not an archival proceedings paper.
    labels = [('국제 학술지', 1, '게재 승인'), ('국제 학회', 1, '워크숍 · Non-archival'), ('국내 학회', 4, 'IEIE · IPIU · ISET · KAIC')] if lang == 'ko' else [
        ('International journal', 1, 'Accepted'), ('International conference', 1, 'Workshop · Non-archival'), ('Domestic conferences', 4, 'IEIE · IPIU · ISET · KAIC')]
    return '<dl class="publication-breakdown" aria-label="' + ('발표 유형별 논문 수' if lang == 'ko' else 'Publication types') + '">' + ''.join(
        f'<div><dt>{esc(label)}</dt><dd>{count}<small>{esc(note)}</small></dd></div>' for label, count, note in labels) + '</dl>'

def refine(site):
    site = Path(site)
    css_name = 'publication-layout-' + hashlib.sha256(CSS.encode()).hexdigest()[:12] + '.css'
    (site / 'projects/assets' / css_name).write_text(CSS, encoding='utf-8')
    report = {'version': VERSION, 'pages': [], 'indexes': []}
    for slug in SLUGS:
        for lang in ('ko', 'en'):
            path = site / 'projects' / slug / lang / 'index.html'
            source = path.read_text(encoding='utf-8')
            if f'data-publication-layout="{VERSION}"' in source:
                report['pages'].append({'slug': slug, 'lang': lang, 'unchanged': True})
                continue
            match = re.search(r'<script type="application/json" id="paper-data">(.*?)</script>', source, re.S)
            if not match:
                raise ValueError('Missing paper payload: ' + slug)
            original_payload = match[1]; paper = json.loads(original_payload)
            source = re.sub(r'<p class="poster-caption">.*?</p>', '', source, flags=re.S)
            # Related research is the last content section, including pages with a poster.
            related = re.search(r'<section\b[^>]*>\s*<h2>(?:함께 살펴볼 연구|Related research)</h2>.*?</section>', source, re.S)
            if not related:
                raise ValueError('Missing related research: ' + slug)
            block = related[0].replace('<section', '<section id="related"', 1)
            source = source[:related.start()] + source[related.end():]
            source = source.replace('</main>', block + '</main>', 1)
            if slug not in CACHE:
                source = re.sub(r'<div\b[^>]*id="explorer"[^>]*>\s*</div>', '', source, flags=re.S)
            # Keep numeric results visible even when caching interaction is useful.
            source = re.sub(r'<noscript>\s*<p class="note">.*?</p>\s*</noscript>', '', source, flags=re.S)
            if slug in {'navila-patch', 'lift3d-film', 'act-cbam'}:
                source = once(source, r'<details class="data-details">.*?</details>',
                              lambda _: '<div class="result-tables">' + static_tables(paper, lang) + '</div>')
            elif slug in CACHE:
                source = once(source, r'<details class="data-details">\s*<summary>.*?</summary>(.*?)</details>',
                              lambda m: '<div class="result-tables">' + m[1] + '</div>')
            # STAR already has four static tables and no manuscript/poster; preserve it.
            if original_payload != re.search(r'<script type="application/json" id="paper-data">(.*?)</script>', source, re.S)[1]:
                raise ValueError('Data payload changed: ' + slug)
            source = source.replace('<main ', f'<main data-publication-layout="{VERSION}" ', 1)
            source = source.replace('</head>', f'<link rel="stylesheet" href="/projects/assets/{css_name}"></head>', 1)
            path.write_text(source, encoding='utf-8')
            report['pages'].append({'slug': slug, 'lang': lang, 'cache_explorer': slug in CACHE,
                                    'related_last': True, 'poster_caption': False})
    for lang in ('ko', 'en'):
        path = site / 'projects' / lang / 'index.html'
        source = path.read_text(encoding='utf-8')
        if 'class="publication-breakdown"' not in source:
            source = once(source, r'(<p class="index-intro">.*?</p>)', lambda m: m[1] + summary(lang))
            source = source.replace('</head>', f'<link rel="stylesheet" href="/projects/assets/{css_name}"></head>', 1)
            path.write_text(source, encoding='utf-8')
        report['indexes'].append({'lang': lang, 'counts': [1, 1, 4]})
    (site / 'projects/layout-status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', required=True, type=Path)
    refine(parser.parse_args().site)
