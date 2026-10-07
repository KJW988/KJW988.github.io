#!/usr/bin/env python3
"""Run the existing artifact checks, allowing only the two verified added PNGs."""
from pathlib import Path
import hashlib
import finalize
from publication_finish import MEDIA_HASHES
# The original allowlist predated author-supplied PNGs. Do not widen it for documents.
site=finalize.ROOT/'_site'
expected={k:v for k,v in MEDIA_HASHES.items() if k.endswith('.png')}
for path in (site/'projects').rglob('*.png'):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest in expected.values(),('Unexpected publication PNG',path)
finalize.PROJECT_EXT.add('.png')
import check
check.main()
