"""Summarise an NCBI BioSample table written by the wrapper (11 comment lines, header on line 12)."""
import collections
import re
import sys

import pandas as pd

MISSING = ('not collected', 'not provided', 'not applicable', 'missing', 'restricted access')
for path in sys.argv[1:]:
    t = pd.read_csv(path, sep='\t', skiprows=11, dtype=str, keep_default_na=False)
    print(f"{path}: {len(t)} rows x {len(t.columns)} cols; unique sample_name {t['*sample_name'].nunique()}")
    mand = [c for c in t.columns if c.startswith('*')]
    for c in mand:
        v = t[c]
        c_ = collections.Counter(v)
        print(f"  {c}: distinct={len(c_)} empty={(v == '').sum()} missing-terms={sum(n for x, n in c_.items() if x.lower().startswith(MISSING))} eg={list(c_)[:3]}")
    allempty = [c for c in t.columns if (t[c] == '').all()]
    print(f"  columns empty for every row ({len(allempty)}): {allempty[:25]}")
    allmissing = [c for c in t.columns if not (t[c] == '').all() and t[c].str.lower().str.startswith(MISSING).all()]
    print(f"  columns all missing-terms ({len(allmissing)}): {allmissing[:25]}")
    dates = collections.Counter(re.sub(r'\d', '9', d) for d in t['*collection_date'])
    print(f"  collection_date forms: {dates.most_common(4)}")
    odd = {c: v for c in t.columns for v in t[c].unique()[:50] if re.search(r'(^|\s)(nan|NaN|None)(\s|$)', v)}
    print(f"  cells with nan/None: {list(odd.items())[:5]}")
    print(f"  sample_title eg: {t['sample_title'].iloc[0] if 'sample_title' in t else None!r}")
