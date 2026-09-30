#!/usr/bin/env python3
"""Install only checksum-approved rendered seminar pages; never source documents."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, tarfile, tempfile, zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ALLOWED = {'.html', '.css', '.js', '.svg', '.webp', '.mp4'}
SAMPLE_SHA = 'ef8ad225ce8018d199cd4261577c35ff9a6f314f8e8d203b8beb99ad2bb32dda'

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def selection(folder=HERE):
    folder = Path(folder)
    manifest_path = folder / 'full-manifest.json'
    missing = []
    if manifest_path.is_file():
        meta = json.loads(manifest_path.read_text(encoding='utf-8'))
        if meta.get('version') != 2 or meta.get('format') != 'tar.xz':
            raise ValueError('Unsupported rendered bundle manifest')
        for part in meta['parts']:
            if not re.fullmatch(r'seminar_complete\.part[0-9]{2}', part['name']):
                raise ValueError('Unsafe bundle-part name')
        missing = [p['name'] for p in meta['parts'] if not (folder/p['name']).is_file()]
        if not missing:
            return 'full', meta, []
    sample = folder / 'seminar_rendered_public.zip'
    if sample.is_file():
        return 'sample', {'deck_count': 3, 'source_slide_count': 9, 'rendered_state_count': 16,
                          'file_count': 31, 'bundle_sha256': SAMPLE_SHA}, missing
    return 'waiting', None, missing

def safe_name(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or not path.parts or path.parts[0] != 'seminars'
            or '..' in path.parts or '\\' in name or path.suffix not in ALLOWED):
        raise ValueError('Unapproved rendered file: ' + name)
    return path

def inspect_files(stage, meta):
    files = [p for p in stage.rglob('*') if p.is_file()]
    if len(files) != meta['file_count']: raise ValueError('Rendered file count mismatch')
    html = (stage/'seminars/index.html').read_text(encoding='utf-8')
    if '<html lang="ko">' not in html or 'data-lang=' in html or '<iframe' in html:
        raise ValueError('Viewer must be Korean-only and not load an external document')
    if re.search(r'(?:href|src)=[\"\'][^\"\']*\.(?:pptx?|pdf|ttf|otf|woff2?)(?:[?#\"\'])', html, re.I):
        raise ValueError('Source document or font URL detected')
    if re.search(r'<a\b[^>]*\bdownload\b', html, re.I):
        raise ValueError('Original download controls are not allowed')
    for file in files:
        if file.suffix == '.svg':
            root = ET.fromstring(file.read_bytes())
            for node in root.iter():
                tag = node.tag.rsplit('}', 1)[-1]
                if tag in {'script', 'foreignObject', 'font', 'font-face', 'text'}:
                    raise ValueError('Unexpected SVG content: ' + str(file))
                for key, value in node.attrib.items():
                    if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:image/')):
                        raise ValueError('SVG external resource detected')
    data = (stage/'seminars/slides.js').read_text(encoding='utf-8').strip()
    prefix = 'window.SEMINAR_DECKS='
    if not data.startswith(prefix) or not data.endswith(';'): raise ValueError('Unexpected deck data format')
    decks = json.loads(data[len(prefix):-1])
    if len(decks) != meta['deck_count']: raise ValueError('Deck count mismatch')
    if sum(len(d['slides']) for d in decks) != meta['source_slide_count']: raise ValueError('Slide count mismatch')
    if sum(len(s['frames']) for d in decks for s in d['slides']) != meta['rendered_state_count']:
        raise ValueError('Rendered state count mismatch')
    for d in decks:
        for s in d['slides']:
            paths = s['frames'] + [s['thumbnail']]
            for m in s.get('media', []): paths.extend([m['src'], m['poster']])
            for path in paths:
                name = 'seminars/' + path
                safe_name(name)
                if not (stage/name).is_file(): raise ValueError('Missing rendered asset: ' + name)
    return decks

def assemble_parts(folder, meta, target):
    h = hashlib.sha256()
    with target.open('wb') as out:
        for part in meta['parts']:
            source = folder/part['name']
            if source.stat().st_size != part['bytes'] or sha256(source) != part['sha256']:
                raise ValueError('Rendered bundle-part checksum mismatch: ' + part['name'])
            with source.open('rb') as f:
                for chunk in iter(lambda: f.read(1024*1024), b''):
                    out.write(chunk); h.update(chunk)
    if target.stat().st_size != meta['bundle_bytes'] or h.hexdigest() != meta['bundle_sha256']:
        raise ValueError('Complete rendered bundle checksum mismatch')

def extract_full(archive, stage, meta):
    seen = set(); total = 0
    with tarfile.open(archive, 'r:xz') as tf:
        for item in tf:
            path = safe_name(item.name)
            if not item.isfile() or item.name in seen:
                raise ValueError('Links, directories or duplicate archive entries are not allowed')
            total += item.size; seen.add(item.name)
            if total > meta['expanded_bytes'] or len(seen) > meta['file_count']:
                raise ValueError('Rendered archive exceeds approved bounds')
            target = stage/path; target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(item) as src, target.open('wb') as dest: shutil.copyfileobj(src, dest)
    if total != meta['expanded_bytes'] or len(seen) != meta['file_count']:
        raise ValueError('Expanded archive size mismatch')

def extract_sample(archive, stage):
    if sha256(archive) != SAMPLE_SHA: raise ValueError('Unapproved sample; never upload original documents')
    seen = set(); total = 0
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path = safe_name(item.filename); total += item.file_size
            if item.filename in seen or (item.external_attr >> 16) & 0o170000 == 0o120000 or total > 20*1024*1024:
                raise ValueError('Unsafe sample archive')
            seen.add(item.filename); target = stage/path; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(item))

def link_navigation(root):
    layout = root/'_layouts/about-home.html'; sidebar = root/'_includes/sidebar.html'
    if layout.is_file():
        text = layout.read_text(encoding='utf-8')
        anchor = '<a href="{{ \'/blog/\' | relative_url }}">{{ p.blog_label }}</a>'
        link = '<a class="seminars-nav" href="{{ \'/seminars/\' | relative_url }}">{% if p.lang == \'en\' %}Seminars{% else %}세미나{% endif %}</a>'
        if 'class="seminars-nav"' not in text:
            if anchor not in text: raise ValueError('About navigation changed; review before replacing')
            layout.write_text(text.replace(anchor, link+'\n      '+anchor, 1), encoding='utf-8')
    if sidebar.is_file():
        text = sidebar.read_text(encoding='utf-8'); anchor = '{% for tab in site.tabs %}'
        link = '<li class="nav-item"><a href="{{ \'/seminars/\' | relative_url }}" class="nav-link"><i class="fa-fw fas fa-chalkboard-teacher"></i><span>세미나</span></a></li>'
        if "'/seminars/'" not in text:
            if anchor not in text: raise ValueError('Sidebar navigation changed; review before replacing')
            sidebar.write_text(text.replace(anchor, link+'\n      '+anchor, 1), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--folder', type=Path, default=HERE)
    parser.add_argument('--require', action='store_true')
    parser.add_argument('--require-full', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args(); mode, meta, missing = selection(args.folder)
    if args.status:
        print(json.dumps({'mode':mode,'missing_parts':missing,'expected':meta},ensure_ascii=False));return
    if args.require_full and mode != 'full': raise SystemExit('Complete rendered bundle not present: '+', '.join(missing))
    if mode == 'waiting':
        if args.require: raise SystemExit('Rendered bundle is not present')
        print('Seminars: no rendered bundle; existing site unchanged.');return
    if missing: print('Complete archive is waiting for parts; preserve the previous sample:', ', '.join(missing))
    args.root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='seminars-') as temp:
        stage = Path(temp)/'stage'; stage.mkdir()
        if mode == 'full':
            archive = Path(temp)/'rendered.tar.xz'; assemble_parts(args.folder, meta, archive); extract_full(archive, stage, meta)
        else: extract_sample(args.folder/'seminar_rendered_public.zip', stage)
        inspect_files(stage, meta)
        target = args.root/'seminars'
        if target.exists(): raise ValueError('Destination exists; refusing to overwrite unrelated source content')
        shutil.copytree(stage/'seminars', target)
        if mode == 'full':
            html_path = target/'index.html'; html = html_path.read_text(encoding='utf-8')
            for name in ['viewer.css','slides.js','viewer.js']:
                html = html.replace('"'+name+'"','"'+name+'?v='+meta['bundle_sha256'][:12]+'"')
            html_path.write_text(html,encoding='utf-8')
    link_navigation(args.root)
    print(f"Seminars {mode}: {meta['deck_count']} decks; {meta['source_slide_count']} source slides; {meta['rendered_state_count']} states. No source documents or fonts.")
if __name__ == '__main__': main()
