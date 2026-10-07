#!/usr/bin/env python3
"""Fail deployment if STAR's retired public research content is restored."""
from pathlib import Path
import argparse, json, re, zipfile

ROOT=Path(__file__).resolve().parents[2]

def verify_source(root):
    source=(root/'tools/research/content.py').read_text(encoding='utf-8')
    start=source.index(" dict(slug='star',")
    end=source.index(" dict(slug='navila-patch',",start)
    block=source[start:end]
    for marker in ("metrics=[]","studies=[]","code=None","Non-archival"):
        assert marker in block,("STAR public source",marker)
    assert len(block)<2400, "STAR metadata record is unexpectedly detailed"
    for retired in ("tools/research/figures/star.webp","tools/site/media/star-overview.json",
                    "tools/site/media/star-overview-e15e57806e1a.svg"):
        assert not (root/retired).exists(),retired
    with zipfile.ZipFile(root/'tools/site/media/publication-rendered-media.zip') as z:
        allowed={"velocity-overview.png","navila-overview.png","velocity-poster.svg","navila-poster.svg"}
        assert set(z.namelist())==allowed,z.namelist()
    english=(root/'tools/research/english_copy.py').read_text(encoding='utf-8')
    assert not re.search(r'\bSTAR\b',english), "Retired STAR editorial copy remains"
    story=(root/'tools/site/publication_story_other.py').read_text(encoding='utf-8')
    assert "D['star']" not in story
    finish=(root/'tools/site/publication_finish.py').read_text(encoding='utf-8')
    assert "star-overview.svg" not in finish and "Table 5 · Overall (2,027 videos)" not in finish
    print("PASS: public source has venue-only STAR metadata and non-STAR media.")

def verify_site(site):
    site=Path(site)
    for lang in ("ko","en"):
        s=(site/f'projects/star/{lang}/index.html').read_text(encoding='utf-8')
        assert 'data-star-public="star-public-header-v1"' in s
        assert 'https://www.autopilot-cvpr.net/' in s
        assert re.search('non-archival',s,re.I)
        for forbidden in ('id="results"','id="method"','id="overview"','paper-data','paper-figure',
                          'star-overview','id="figure-dialog"','data-research-story='):
            assert forbidden not in s,(lang,forbidden)
        listing=(site/f'projects/{lang}/index.html').read_text(encoding='utf-8')
        assert 'class="star-archive-cover"' in listing
        assert 'STAR: Stage-wise Traffic Accident Detection via Optical-Flow-Guided Reasoning' in listing
    assert not (site/'projects/assets/star.webp').exists()
    assert not any((site/'projects/assets').glob('star-overview*'))
    print("PASS: STAR site metadata-only in both languages; no overview image or result tables.")

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path)
    ap.add_argument('--site',type=Path)
    args=ap.parse_args()
    if args.source:verify_source(args.source)
    if args.site:verify_site(args.site)
    assert args.source or args.site
