#!/usr/bin/env python3
"""Run existing bilingual UI regressions with the current shared narrative copy.

Only expected editorial strings are updated. Numerical data, navigation, motion,
retired paths, source links and all original assertions are retained.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/research'))
from content import PAPERS
from presentation import COPY
from publication_story import apply_story_copy
apply_story_copy(PAPERS)
import verify_polish
import verify_english

if __name__=='__main__':
    verify_polish.main()
    verify_english.main()
