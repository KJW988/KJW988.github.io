#!/usr/bin/env python3
"""한·영 경로, 원문 링크·그림, 개인정보 제외, 핵심 실험 수치를 검사합니다."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import json
import math
from content import PAPERS
from publish import ROOT, PAPER_IDS, paper_url

class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs, self.paper_links = [], [], []
        self.lang, self.h1, self.canonical, self.figures = None, 0, 0, 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang')
        if tag == 'h1': self.h1 += 1
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical += 1
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'a' and 'paper-link' in a.get('class', '').split(): self.paper_links.append(a.get('href'))
        if tag == 'img' and a.get('src', '').endswith('.webp'): self.figures += 1
        for key in ('src', 'href'):
            if key in a: self.refs.append(a[key])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'projects')
    out = parser.parse_args().output.resolve()
    errors, checked = [], []
    pages = list(out.rglob('*.html'))
    assert len(PAPERS) == 6 and len(pages) == 21
    for path in pages:
        content = path.read_text(encoding='utf-8')
        s = Scan(); s.feed(content)
        if len(s.ids) != len(set(s.ids)): errors.append(f'중복 ID: {path}')
        if path.parent.name in ('ko', 'en'):
            if s.lang != path.parent.name or s.h1 != 1 or s.canonical != 1:
                errors.append(f'언어/제목/canonical: {path}')
            if 'class="blog-back"' not in content:
                errors.append(f'블로그 복귀 링크 누락: {path}')
            slug = path.parent.parent.name
            if slug in PAPER_IDS:
                if 'class="method-copy"' not in content or 'class="walkthrough"' in content or 'data-step=' in content:
                    errors.append(f'방법 설명 읽기 구조: {path}')
                if s.paper_links != [paper_url(slug)] or s.figures != 1:
                    errors.append(f'원문 링크/그림: {path}')
        for ref in s.refs:
            u = urlsplit(ref)
            if u.scheme or ref.startswith('//'): continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            if not target.exists(): errors.append(f'없는 로컬 파일 {ref}: {path}')
            elif u.fragment and not u.path and unquote(u.fragment) not in s.ids:
                errors.append(f'없는 앵커 {ref}: {path}')
        for excluded in ('X-Amz-', 'private-user-images', '4257-8589', 'Date of Birth', 'Lorem ipsum'):
            if excluded in content: errors.append(f'공개 제외 대상 {excluded}: {path}')
        checked.append(str(path.relative_to(out)))
    for p in PAPERS:
        assert (out / 'assets' / f'{p["slug"]}.webp').is_file()
        for m in p.get('cache', []):
            for r in m['rows']:
                assert sum(i % r[0] == 0 for i in range(m['N'])) == math.ceil(m['N'] / r[0])
    assert PAPERS[2]['authors'][:2] == ['Jaesung Sung*', 'Jiwon Kim*']
    assert PAPERS[0]['cache'][0]['rows'][-1][4:] == [119.5, 13.50, 2.71]
    assert PAPERS[1]['cache'][0]['rows'][-1][4:] == [118.4, 14.91, 2.79]
    assert PAPERS[4]['studies'][0]['rows'][-1] == ['sweep into', 74, 72, 82]
    assert sum(r[3] is None for r in PAPERS[4]['studies'][0]['rows']) == 4
    assert PAPERS[2]['studies'][0]['rows'][-1] == ['STAR', .502, .529, .530, .520]
    assert PAPERS[3]['studies'][0]['rows'][-1][3] == 38.6
    report = {'status': 'failed' if errors else 'passed', 'html_pages': len(pages),
              'localized_pages': 14, 'paper_links': 12, 'figures': 6, 'errors': errors, 'checked': checked,
              'scope': '정적 검사. 외부 원문 공유 권한과 브라우저 테스트는 별도입니다.'}
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if errors: raise SystemExit('\n'.join(errors))
    print('검사 통과: 한·영 본문 14개, 진입점 7개, 원문 링크 12개, 그림 6개, 로컬 경로 및 핵심 실험값')

if __name__ == '__main__':
    main()
