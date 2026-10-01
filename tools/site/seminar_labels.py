"""Display-only seminar labels; original slide IDs and rendered assets stay intact."""
from pathlib import Path
import re


def refine_seminar_labels(site):
    directory = Path(site) / 'seminars'
    script, page = directory / 'viewer.js', directory / 'index.html'
    if not script.is_file() or not page.is_file():
        return
    js = script.read_text(encoding='utf-8')
    if '// seminar-cover-zero-v1' not in js:
        def replace(old, new):
            nonlocal js
            if js.count(old) != 1:
                raise ValueError('Seminar numbering anchor changed: ' + old)
            js = js.replace(old, new, 1)
        replace('  function deck() { return decks[di]; }', r'''  // seminar-cover-zero-v1
  function deck() { return decks[di]; }
  function pageOffset(d = deck()) { return /\bPDF\b/i.test(d.description || '') ? 0 : 1; }
  function displayPage(s, d = deck()) { return s.original - pageOffset(d); }
  function lastPage(d = deck()) { return d.originalCount - pageOffset(d); }''')
        replace('`${s.original}페이지: ${s.label}`', '`${displayPage(s)}페이지: ${s.label}`')
        replace('String(s.original)', 'String(displayPage(s))')
        replace('`${d.title} · ${s.original}페이지`', '`${d.title} · ${displayPage(s, d)}페이지`')
        replace('`${s.original} / ${d.originalCount}`', '`${displayPage(s, d)} / ${lastPage(d)}`')
        replace('((si+1)/d.slides.length*100)', '((si+1-pageOffset(d))/Math.max(1,d.slides.length-pageOffset(d))*100)')
        script.write_text(js, encoding='utf-8')
    html = page.read_text(encoding='utf-8')
    html = re.sub(r'<p class="sample-note"[^>]*>.*?</p>', '', html, flags=re.S)
    html = re.sub(r'(src="viewer\.js)(?:\?[^"\s<>]*)?', r'\1?v=20261001-cover-zero-v1', html)
    if 'data-page-numbering="ppt-cover-zero-v1"' not in html:
        html = html.replace('<section id="player"', '<section data-page-numbering="ppt-cover-zero-v1" id="player"', 1)
    page.write_text(html, encoding='utf-8')
