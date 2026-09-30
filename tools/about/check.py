#!/usr/bin/env python3
"""Validate the built About home and absence of the unpublished post."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / '_site'
class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags = []; self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

def main():
    for route, lang in [('index.html', 'ko'), ('en/index.html', 'en')]:
        text = (SITE / route).read_text(encoding='utf-8'); doc = Document(text)
        assert ('html', {'lang': lang}) in doc.tags
        assert sum(t == 'h1' for t, _ in doc.tags) == 1
        assert 'Learning That' in text and '2027' in text
        assert '{{' not in text and '{%' not in text
        assert not any(t in ('iframe', 'button') for t, _ in doc.tags)
        assert '4257-8589' not in text and '1998.08.31' not in text
        for tag, attr in doc.tags:
            url = attr.get('href', '') if tag in ('a', 'link') else attr.get('src', '')
            if not url or not url.startswith('/'): continue
            path = SITE / unquote(urlsplit(url).path).lstrip('/')
            if path.is_dir(): path = path / 'index.html'
            assert path.is_file(), (route, url)
    assert (SITE / 'blog/index.html').is_file()
    assert (SITE / 'about/index.html').is_file()
    assert not (SITE / 'posts/4th-semester-goals/index.html').exists()
    for path in SITE.rglob('*'):
        if path.suffix not in ('.html', '.json', '.xml'): continue
        text = path.read_text(encoding='utf-8')
        assert '4학기 목표 정리' not in text and '4th-semester-goals' not in text, path
    print('About home: Korean/English markup, internal links, privacy and post removal PASS')

if __name__ == '__main__': main()
