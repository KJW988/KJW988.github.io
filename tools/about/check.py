#!/usr/bin/env python3
"""Validate the built About home and absence of the unpublished post."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs
import re

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
        assert not any(t == 'iframe' for t, _ in doc.tags)
        buttons = [a for t, a in doc.tags if t == 'button']
        assert len(buttons) == 1 and buttons[0].get('id') == 'copy-email'
        elements = {a['id']: a for _, a in doc.tags if 'id' in a}
        email = elements['contact-email']['data-email']
        assert email == 'zw0831@kookmin.ac.kr'
        assert elements['email-app']['href'] == 'mailto:' + email
        gmail = urlsplit(elements['email-gmail']['href'])
        assert gmail.scheme == 'https' and gmail.netloc == 'mail.google.com'
        assert parse_qs(gmail.query)['url'] == ['mailto:' + email]
        assert any(t == 'a' and a.get('href') == '#contact-email' for t, a in doc.tags)
        assert 'hidden' in buttons[0]  # No dead copy button without JavaScript.
        if lang == 'ko':
            assert '국민대학교 컴퓨터공학과 석사과정' in text
            assert '인공지능 연구실(MI Lab), 지도교수: 이재구' in text
            assert '국민대학교 컴퓨터공학 석사과정' not in text
        else:
            assert 'Machine Intelligence Lab. (MI Lab), Advisor: Prof. Jaekoo Lee' in text
        assert not re.search(r'(?:\+82\s?10|010)[\s-]?\d{4}[\s-]?\d{4}', text)
        assert 'date of birth' not in text.lower() and '생년월일' not in text
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
    print('About home: affiliation, contact routes, Korean/English markup, internal links, privacy and post removal PASS')

if __name__ == '__main__': main()
