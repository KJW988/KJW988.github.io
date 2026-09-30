#!/usr/bin/env python3
"""Minimize the Pages artifact. This does not delete tracked sources or Git history."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from html import escape

ROOT=Path(__file__).resolve().parents[2]
PUBLIC_FILES={'index.html','en/index.html','about/index.html','research/index.html',
 'assets/css/about.css','assets/css/about-sections.css',
 'assets/js/about.js','assets/js/about-contact.js',
 'assets/img/profile/main2.jpg'}
PROJECT_EXT={'.html','.css','.js','.svg','.webp','.csv','.json','.xml'}
SEMINAR_EXT={'.html','.css','.js','.svg','.webp','.mp4'}
RETIRED=('blog','posts','categories','tags','archives','page2','assets/js/data','assets/img/posts')
BASE='https://kjw988.github.io'

def keep(path):
    s=path.as_posix()
    return s in PUBLIC_FILES or (s.startswith('projects/') and path.suffix in PROJECT_EXT) or (s.startswith('seminars/') and path.suffix in SEMINAR_EXT)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',type=Path,default=ROOT/'_site');args=parser.parse_args();site=args.site.resolve()
    if not (site/'index.html').is_file():raise SystemExit('Refusing to operate without a built homepage')
    removed=[]
    for file in list(site.rglob('*')):
        if file.is_file() and not keep(file.relative_to(site)):
            removed.append(file.relative_to(site).as_posix());file.unlink()
    for d in sorted([p for p in site.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):
        if not any(d.iterdir()):d.rmdir()
    # Also cover navigation inside the checksum-approved seminar package.
    for p in site.rglob('*.html'):
        text=p.read_text(encoding='utf-8')
        text=re.sub(r'<a\b[^>]*href=[\"\'](?:https://kjw988\.github\.io)?/blog/[^\"\']*[\"\'][^>]*>.*?</a>','',text,flags=re.S|re.I)
        text=text.replace('연구 프로젝트','연구 출판물').replace('Research projects','Publications')
        text=text.replace('>← 블로그<','>← 홈<').replace('>← Blog<','>← Home<')
        text=text.replace('>블로그</a>','>홈</a>').replace('>Blog</a>','>Home</a>')
        text=re.sub(r'(<a\b[^>]*href="/projects/ko/"[^>]*>)연구(</a>)',r'\1연구 출판물\2',text)
        if '/assets/js/privacy-reset.js' not in text:
            text=text.replace('</head>','<script src="/assets/js/privacy-reset.js" defer></script></head>',1)
        p.write_text(text,encoding='utf-8')
    # Retire the old Chirpy worker so returning online visitors stop receiving cached posts.
    (site/'sw.min.js').write_text("""'use strict';
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  for(const key of await caches.keys()){if(key.startsWith('chirpy-'))await caches.delete(key);}
  await self.clients.claim();
  await self.registration.unregister();
})()));
// No fetch handler: no offline blog responses or new cached pages.
""",encoding='utf-8')
    js=site/'assets/js/privacy-reset.js';js.parent.mkdir(parents=True,exist_ok=True)
    js.write_text("""'use strict';
(async()=>{
  try{
    if('caches' in window)for(const key of await caches.keys())if(key.startsWith('chirpy-'))await caches.delete(key);
    if('serviceWorker' in navigator){
      const r=await navigator.serviceWorker.getRegistration('/');
      if(r&&new URL(r.scope).origin===location.origin&&new URL(r.scope).pathname==='/'){
        await r.update().catch(()=>{});await r.unregister();
      }
    }
  }catch(_){}
})();
""",encoding='utf-8')
    (site/'404.html').write_text('''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>페이지를 찾을 수 없습니다 · Jiwon Kim</title><style>body{margin:0;font:16px/1.8 system-ui,sans-serif;color:#22283a}main{max-width:680px;margin:18vh auto;padding:24px}h1{font-size:28px}a{color:inherit;margin-right:20px}</style><script src="/assets/js/privacy-reset.js" defer></script></head><body><main><p>404</p><h1>페이지를 찾을 수 없습니다.</h1><p>요청한 페이지는 공개되어 있지 않습니다.</p><a href="/">About me</a><a href="/projects/ko/">연구 출판물</a><a href="/seminars/">세미나</a></main></body></html>''',encoding='utf-8')
    urls=[]
    for p in site.rglob('index.html'):
        rel=p.relative_to(site).as_posix()
        if rel.startswith(('about/','research/')) or rel=='projects/index.html':continue
        if rel.startswith('projects/') and not rel.endswith(('ko/index.html','en/index.html')):continue
        urls.append(BASE+'/'+rel.removesuffix('index.html'))
    (site/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(u)+'</loc></url>' for u in sorted(urls))+'</urlset>',encoding='utf-8')
    (site/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'/sitemap.xml\n',encoding='utf-8')
    for prefix in RETIRED:assert not (site/prefix).exists(),prefix
    for p in site.rglob('*.html'):
        s=p.read_text(encoding='utf-8')
        assert not re.search(r'href=[\"\'](?:https://kjw988\.github\.io)?/(?:blog|posts|archives|categories|tags)(?:/|[\"\'])',s),p
        assert '4학기 목표 정리' not in s and '4th-semester-goals' not in s,p
    report={'retired_paths':list(RETIRED),'removed_file_count':len(removed),'source_files_deleted':False,'public_routes':sorted(urls)}
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
