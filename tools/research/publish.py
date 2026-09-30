#!/usr/bin/env python3
"""공개용 빌드: 원문 그림과 저자 지정 링크를 포함한 정적 페이지 생성."""
from pathlib import Path
from html import escape
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from content import PAPERS
from presentation import refine_output

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'https://kjw988.github.io/projects'
# 저자의 기존 포트폴리오에서 논문 제목과 대응을 확인한 원문 링크.
PAPER_IDS = {
    'endcache': '12ajhzw5ExPX5JAXDPPqiTl5oxPjNnYKJ',
    'velocity-reuse': '1aRu4psdRBYXHJ4ROHrtvJ49hq3avxzy-',
    'star': '1L7EaOh1gzy6Ux2ThxCyijN9nzPY0qQbw',
    'navila-patch': '1SsiQI2jXnYUctJ3BEyx6-YnIqTIp0jme',
    'lift3d-film': '1yDGhQfbfSDdnVuxdVtTUTfcRo4HpYdWS',
    'act-cbam': '1ym1AjDs3jplHEfL1hs-Ni-3D80SVnOPi',
}
FIGURES = {
    'endcache': '17c478c0d167a24ef3f9a2a460bd9ae66a4bd57c',
    'velocity-reuse': '142940d9e787069b82e6d4d9bef541403868cc0b',
    'star': 'b074f4bc7c75848e77ce585d3f0f0a1ac2cd0b10',
    'navila-patch': '60d87e6a119c8238b6e58c1a7ab26f8035b6265e',
    'lift3d-film': '1ac8c97ce1204e44355d8c0768bed8a2ccf05a53',
    'act-cbam': 'b3e1b8505a54abed1b68c83ed7cc50d4635bb9f2',
}
STAR_CODE = 'https://github.com/Sung-Jae-Seong/CVPR-w_ACCIDENT-CHALLENGE_STAR'

def paper_url(slug):
    return f'https://drive.google.com/file/d/{PAPER_IDS[slug]}/view?usp=sharing'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'projects')
    out = parser.parse_args().output.resolve()
    assets = out / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    if set(PAPER_IDS) != {p['slug'] for p in PAPERS}:
        raise ValueError('논문 목록과 원문 링크가 일치하지 않습니다.')
    for slug, expected in FIGURES.items():
        src = HERE / 'figures' / f'{slug}.webp'
        raw = src.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != expected:
            raise ValueError(f'원문 그림 무결성 검사 실패: {slug}')
        shutil.copyfile(src, assets / src.name)
    subprocess.run([sys.executable, str(HERE / 'build.py'), '--output', str(out)], check=True)
    refine_output(out, PAPERS)
    for p in PAPERS:
        slug = p['slug']
        url = paper_url(slug)
        bib = p['bibtex'].rstrip()[:-1].rstrip() + ',\n  url={' + url + '}\n}'
        for lang in ('ko', 'en'):
            path = out / slug / lang / 'index.html'
            page = path.read_text(encoding='utf-8')
            label = '논문 PDF · Google Drive' if lang == 'ko' else 'Paper PDF · Google Drive'
            button = f'<a class="pill primary paper-link" href="{escape(url)}" target="_blank" rel="noopener noreferrer">↗ {label}</a>'
            if slug == 'star':
                button += f'<a class="pill primary" href="{STAR_CODE}">↗ {"공개 코드" if lang == "ko" else "Code"}</a>'
            page = page.replace('<div class="links">', '<div class="links">' + button, 1)
            page = re.sub(r'<pre id="bibtex">.*?</pre>', lambda _: '<pre id="bibtex">' + escape(bib) + '</pre>', page, count=1, flags=re.S)
            metadata = f'<meta property="og:image" content="{BASE}/assets/{slug}.webp"><meta name="citation_title" content="{escape(p["formal_title"])}">'
            page = page.replace('</head>', metadata + '</head>', 1)
            path.write_text(page, encoding='utf-8')
    manifest = {'paper_links': {s: paper_url(s) for s in PAPER_IDS}, 'figures_git_sha1': FIGURES,
                'note': '원문 링크의 공유 권한은 변경하지 않습니다. 전체 PDF와 비공개 코드는 배포하지 않습니다.'}
    (out / 'sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('공개용 빌드 완료: 원문 그림 6개, 논문 링크 6개 × 한·영 2종')

if __name__ == '__main__':
    main()
