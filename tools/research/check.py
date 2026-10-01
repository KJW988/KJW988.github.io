#!/usr/bin/env python3
"""Validate the pre-finalized publication build, including author-directed manuscript removal."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import argparse,json,math
from content import PAPERS
from publish import ROOT,PAPER_IDS,paper_url
class Scan(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.refs=[];self.links=[];self.h1=0;self.canonical=0;self.lang=None;self.figures=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='html':self.lang=a.get('lang')
  if tag=='h1':self.h1+=1
  if tag=='link' and a.get('rel')=='canonical':self.canonical+=1
  if 'id' in a:self.ids.append(a['id'])
  if tag=='a' and 'paper-link' in a.get('class','').split():self.links.append(a.get('href'))
  if tag=='img' and a.get('src','').endswith('.webp'):self.figures+=1
  for k in ('src','href'):
   if k in a:self.refs.append(a[k])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'projects');out=ap.parse_args().output.resolve();pages=list(out.rglob('*.html'));errors=[]
 assert len(PAPERS)==6 and len(pages)==21
 for path in pages:
  text=path.read_text();s=Scan();s.feed(text)
  if len(s.ids)!=len(set(s.ids)):errors.append(f'duplicate ids {path}')
  if path.parent.name in ('ko','en'):
   assert s.lang==path.parent.name and s.h1==s.canonical==1
   assert 'class="blog-back"' in text
   slug=path.parent.parent.name
   if slug in PAPER_IDS:
    assert 'class="method-copy"' in text and 'class="walkthrough"' not in text and 'data-step=' not in text
    assert s.links==([paper_url(slug)] if paper_url(slug) else []) and s.figures==1
  for ref in s.refs:
   u=urlsplit(ref)
   if u.scheme or ref.startswith('//'):continue
   target=(path.parent/unquote(u.path)).resolve() if u.path else path
   if not target.exists():errors.append(f'missing {ref}: {path}')
   elif u.fragment and not u.path and unquote(u.fragment) not in s.ids:errors.append(f'missing anchor {ref}: {path}')
  for excluded in ('X-Amz-','private-user-images','4257-8589','Date of Birth','Lorem ipsum'):
   assert excluded not in text
 for p in PAPERS:
  assert (out/'assets'/f'{p["slug"]}.webp').is_file()
  for m in p.get('cache',[]):
   for r in m['rows']:assert sum(i%r[0]==0 for i in range(m['N']))==math.ceil(m['N']/r[0])
 assert PAPERS[2]['authors'][:2]==['Jaesung Sung*','Jiwon Kim*']
 assert PAPERS[0]['cache'][0]['rows'][-1][4:]==[119.5,13.50,2.71]
 assert PAPERS[1]['cache'][0]['rows'][-1][4:]==[118.4,14.91,2.79]
 assert PAPERS[4]['studies'][0]['rows'][-1]==['sweep into',74,72,82]
 assert sum(r[3] is None for r in PAPERS[4]['studies'][0]['rows'])==4
 assert PAPERS[2]['studies'][0]['rows'][-1]==['STAR',.502,.529,.530,.520]
 assert PAPERS[3]['studies'][0]['rows'][-1][3]==38.6
 d=json.loads((out/'sources.json').read_text());assert 'star' not in d['paper_links'] and len(d['paper_links'])==5
 report={'status':'failed' if errors else 'passed','html_pages':len(pages),'paper_links':10,'star_manuscript_excluded':True,'errors':errors}
 (out/'validation.json').write_text(json.dumps(report,indent=2))
 if errors:raise SystemExit('\n'.join(errors))
 print('PASS: 21 pages, 10 manuscript links; STAR manuscript excluded; data unchanged.')
if __name__=='__main__':main()
