#!/usr/bin/env python3
"""Install approved author overviews at their full pixel dimensions.

The encoded web copies derive from camera_ready_fig.png and overview.jpeg.
They are not byte-identical originals. Decode the verified transfer and export
its pixels losslessly to WebP; do not resize, crop or change figure labels.
"""
from pathlib import Path
import argparse, base64, hashlib, io, json, re
from PIL import Image

HERE = Path(__file__).resolve().parent
VERSION = 'author-overviews-20261002-v2'
FIGURES = {
    'lift3d-film': {
        'source_name': 'camera_ready_fig.png',
        'source_sha256': 'f8db588283c16e74002517257a78d2feb4139bb7907ea518064f650aa1e6159d',
        'transfer_sha256': '3bf82c02dc8c7aee556bf0c08c377bbc0d58dca9a43243803b61bb47a60708b3',
        'transfer_bytes': 150960, 'parts': 13, 'dimensions': [2048, 1008],
    },
    'act-cbam': {
        'source_name': 'overview.jpeg',
        'source_sha256': '4bd7be0fc0550161eebcfad8dfe6052fd6ce40e37255dac68cb6cc287b327d9e',
        'transfer_sha256': 'dd6156b2a43492b7ab4812bbff9cfe660b74a650ff4a4b20786fb390355d453a',
        'transfer_bytes': 60996, 'parts': 6, 'dimensions': [1915, 665],
    },
}

def refine(site: Path) -> dict:
    site = Path(site)
    assets = site / 'projects/assets'
    if not assets.is_dir():
        raise ValueError('Run after the public site has been built')
    report = {'version': VERSION, 'figures': {}, 'pages': []}
    for slug, spec in FIGURES.items():
        folder = HERE / 'author_figures' / slug
        expected = [f'part{i:02}.b64' for i in range(1, spec['parts'] + 1)]
        if sorted(p.name for p in folder.glob('part*.b64')) != expected:
            raise ValueError('Incomplete image transfer: ' + slug)
        raw = base64.b64decode(''.join((folder / n).read_text(encoding='ascii') for n in expected), validate=True)
        if len(raw) != spec['transfer_bytes'] or hashlib.sha256(raw).hexdigest() != spec['transfer_sha256']:
            raise ValueError('Image transfer checksum mismatch: ' + slug)
        image = Image.open(io.BytesIO(raw)); image.load()
        if list(image.size) != spec['dimensions']:
            raise ValueError('Image dimensions changed: ' + slug)
        pixel_hash = hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()
        stream = io.BytesIO()
        image.save(stream, format='WEBP', lossless=True, exact=True, method=6)
        data = stream.getvalue(); check = Image.open(io.BytesIO(data)); check.load()
        if check.convert('RGBA').tobytes() != image.convert('RGBA').tobytes():
            raise ValueError('WebP export changed decoded pixels')
        digest = hashlib.sha256(data).hexdigest()
        filename = f'{slug}-author-{digest[:12]}.webp'
        (assets / filename).write_bytes(data)
        report['figures'][slug] = {**spec, 'file': filename, 'sha256': digest,
                                   'decoded_rgba_sha256': pixel_hash, 'bytes': len(data)}
    for path in site.rglob('*.html'):
        before = path.read_text(encoding='utf-8'); after = before
        for slug, spec in report['figures'].items():
            after = after.replace(slug + '.webp', spec['file'])
            def dimensions(match):
                tag = re.sub(r'\s(?:width|height|data-author-overview)="[^"]*"', '', match[0])
                width, height = spec['dimensions']
                return tag[:-1] + f' data-author-overview="{VERSION}" width="{width}" height="{height}">'
            after = re.sub(r'<img\b[^>]*' + re.escape(spec['file']) + r'[^>]*>', dimensions, after)
        if 'data-author-overview=' in after and 'id="author-overview-layout"' not in after:
            after = after.replace('</head>', '<style id="author-overview-layout">.paper-figure img[data-author-overview]{height:auto;max-height:none}</style></head>', 1)
        if after != before:
            path.write_text(after, encoding='utf-8')
            report['pages'].append(path.relative_to(site).as_posix())
    for slug, spec in report['figures'].items():
        for lang in ('ko', 'en'):
            path = site / 'projects' / slug / lang / 'index.html'
            text = path.read_text(encoding='utf-8')
            if spec['file'] not in text or slug + '.webp' in text:
                raise ValueError('Stale detail-page figure: ' + str(path))
            if spec['file'] not in (site / 'projects' / lang / 'index.html').read_text(encoding='utf-8'):
                raise ValueError('Stale Publication thumbnail: ' + slug)
    for route in ('index.html', 'en/index.html'):
        if report['figures']['lift3d-film']['file'] not in (site / route).read_text(encoding='utf-8'):
            raise ValueError('Stale home thumbnail: ' + route)
    for slug in FIGURES:
        (assets / (slug + '.webp')).unlink(missing_ok=True)
    (site / 'projects/author-figures.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    refine(parser.parse_args().site)
