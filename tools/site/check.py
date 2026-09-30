#!/usr/bin/env python3
"""Fail the deployment if a retired blog surface leaks into the public artifact."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote, urljoin
import sys
from finalize import ROOT, RETIRED, keep
sys.path.insert(0,str(ROOT/'tools/research'))
from content import PAPERS
from headings import INTRO_KO, publication_title

class Doc(HTMLParser):
    def __init__(self,text):super().__init__();self.tags=[];self.feed(text)
    def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))

def main():
    site=ROOT/'_site'
    for prefix in RETIRED:assert not (site/prefix).exists(),prefix
    for p in site.rglob('*'):
        if p.is_file():
            rel=p.relative_to(site)
            assert keep(rel) or rel.as_posix() in {'404.html','sitemap.xml','robots.txt','sw.min.js','assets/js/privacy-reset.js'},rel
    for lang,route in [('ko','index.html'),('en','en/index.html')]:
        text=(site/route).read_text();doc=Doc(text)
        assert '<p class="about-closing"><strong><mark>' in text
        assert 'contact_title' not in text and '{{' not in text
        assert 'email-app' not in text and 'email-gmail' not in text and 'email-hint' not in text
        assert sum(t=='button' for t,a in doc.tags)==1
        if lang=='ko':assert '논문 전체보기(6)' in text and '106개 팀 중 6위' in text
        assert sum(t=='a' and 'award-link' in a.get('class','') for t,a in doc.tags)==4
        assert sum(t=='span' and a.get('class')=='award-description' for t,a in doc.tags)==4
    for path in site.rglob('*.html'):
        text=path.read_text();doc=Doc(text)
        for tag,a in doc.tags:
            link=a.get('href',a.get('src',''))
            if not link:continue
            u=urlsplit(link)
            if u.scheme or link.startswith('//'):continue
            route=urljoin('/'+path.relative_to(site).as_posix(),u.path)
            target=site/unquote(route).lstrip('/')
            if target.is_dir():target=target/'index.html'
            assert target.is_file(),(path,link)
    for lang in ('ko','en'):
        text=(site/'projects'/lang/'index.html').read_text()
        if lang=='ko':assert INTRO_KO in text
        for p in PAPERS:assert publication_title(p,lang) in text.replace('&amp;','&')
    print('PASS: retired blog absent; exact titles, biography highlight, contact, award descriptions and internal paths.')
if __name__=='__main__':main()
