#!/usr/bin/env python3
"""Install a checksum-verified, rendered-only Korean seminar bundle before Jekyll.
Original presentations, PDFs, notes and font files are never accepted.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import zipfile

EXPECTED_SHA256 = 'ef8ad225ce8018d199cd4261577c35ff9a6f314f8e8d203b8beb99ad2bb32dda'
ALLOWED = {'.html', '.css', '.js', '.svg', '.webp', '.mp4'}
ROOT = Path(__file__).resolve().parents[2]


def validate(bundle: Path) -> list[str]:
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Approved rendered-only bundle checksum mismatch; do not upload the original archive.')
    with zipfile.ZipFile(bundle) as z:
        infos = z.infolist()
        if len(infos) != 31 or sum(i.file_size for i in infos) > 20 * 1024 * 1024:
            raise ValueError('Unexpected bundle size or file count')
        names = []
        for item in infos:
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or path.parts[0] != 'seminars' or path.suffix not in ALLOWED
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError(f'Unapproved archive entry: {item.filename}')
            if item.filename in names:
                raise ValueError('Duplicate archive path')
            names.append(item.filename)
            if path.suffix == '.svg':
                svg = z.read(item).decode('utf-8')
                if re.search(r'<(?:script|foreignObject|font|font-face)(?:\s|>)', svg):
                    raise ValueError('SVG contains unexpected active content or fonts')
                if re.search(r'data:(?:font|application/(?:x-font|vnd.ms-fontobject))', svg):
                    raise ValueError('Embedded font file is not allowed')
        html = z.read('seminars/index.html').decode('utf-8')
        if re.search(r'(?:href|src)=[\"\"][^\"\"]*\.(?:pptx?|pdf|ttf|otf|woff2?)(?:[?#\"\"])', html, re.I):
            raise ValueError('Source-document or font-file link detected')
        if 'data-lang=' in html or '<html lang="ko">' not in html:
            raise ValueError('The seminar viewer must be Korean-only')
        return names


def link_navigation(root: Path) -> None:
    # Build-only insertion: no broken menu before rendered assets arrive.
    layout = root / '_layouts/about-home.html'
    sidebar = root / '_includes/sidebar.html'
    if layout.is_file():
        text = layout.read_text(encoding='utf-8')
        anchor = '<a href="{{ \'/blog/\' | relative_url }}">{{ p.blog_label }}</a>'
        link = '<a class="seminars-nav" href="{{ \'/seminars/\' | relative_url }}">{% if p.lang == \'en\' %}Seminars{% else %}세미나{% endif %}</a>'
        if 'class="seminars-nav"' not in text:
            if anchor not in text:
                raise ValueError('About navigation changed; review before installing')
            layout.write_text(text.replace(anchor, link + '\n      ' + anchor, 1), encoding='utf-8')
    if sidebar.is_file():
        text = sidebar.read_text(encoding='utf-8')
        anchor = '{% for tab in site.tabs %}'
        link = '<li class="nav-item"><a href="{{ \'/seminars/\' | relative_url }}" class="nav-link"><i class="fa-fw fas fa-chalkboard-teacher"></i><span>세미나</span></a></li>'
        if "'/seminars/'" not in text:
            if anchor not in text:
                raise ValueError('Sidebar navigation changed; review before installing')
            sidebar.write_text(text.replace(anchor, link + '\n      ' + anchor, 1), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT/'tools/seminars/seminar_rendered_public.zip')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--require', action='store_true')
    args = parser.parse_args()
    if not args.bundle.is_file():
        if args.require:
            raise SystemExit('Rendered-only bundle is not present')
        print('Seminars: waiting for the rendered-only bundle; existing site and menus unchanged.')
        return
    names = validate(args.bundle)
    args.root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='seminars-') as temp:
        stage = Path(temp)
        with zipfile.ZipFile(args.bundle) as z:
            for name in names:
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
        target = args.root / 'seminars'
        if target.exists():
            raise ValueError('Destination already exists; refuse to overwrite unrelated content')
        shutil.copytree(stage/'seminars', target)
    link_navigation(args.root)
    print('Seminars installed: 3 excerpt decks, 9 source slides, 16 rendered states; no original documents or fonts.')


if __name__ == '__main__':
    main()
