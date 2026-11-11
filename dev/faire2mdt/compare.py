"""Compare the Galaxy driver's MDT workbook with upstream-by-hand's, sheet by sheet.

Usage: python -I compare.py OUT_DIR   (the OUT_DIR given to run_examples.sh)
Prints, for each case where both ran, the sheet shapes and the cells that differ, grouped as
dates (an Excel serial number by hand, a date in Galaxy), numbers (same value, other digits) and
other.
"""
import glob
import re
import sys
from pathlib import Path

import pandas as pd


def kind(a, b):
    try:
        fa, fb = float(a), float(b)
    except ValueError:
        return 'other'
    except TypeError:
        return 'other'
    if fa == fb or abs(fa - fb) <= 1e-12 * max(abs(fa), abs(fb)):
        return 'numbers'
    return 'other'


def date_kind(a, b):
    if re.fullmatch(r'\d+(\.\d+)?', str(a)) and re.fullmatch(r'\d{4}-\d\d-\d\d(T[\d:]+)?|\d\d:\d\d:\d\d', str(b)):
        return 'dates'
    return None


out = Path(sys.argv[1])
for d in sorted(out.iterdir()):
    if not d.is_dir():
        continue
    hand = glob.glob(str(d / 'by_hand' / '*_MDTfmt.xlsx'))
    gal = d / 'galaxy' / 'mdt.xlsx'
    if not hand or not gal.exists():
        print(f'{d.name}: by hand {"ran" if hand else "failed"}, Galaxy {"ran" if gal.exists() else "failed"}')
        continue
    h = pd.read_excel(hand[0], sheet_name=None, header=None, dtype=str)
    g = pd.read_excel(gal, sheet_name=None, header=None, dtype=str)
    parts = []
    for sheet in h:
        a, b = h[sheet].fillna(''), g[sheet].fillna('')
        if a.shape != b.shape:
            parts.append(f'{sheet} shape {a.shape} by hand, {b.shape} Galaxy')
            continue
        counts, examples = {}, {}
        for i in range(a.shape[0]):
            for j in range(a.shape[1]):
                x, y = a.iat[i, j], b.iat[i, j]
                if x != y:
                    k = date_kind(x, y) or kind(x, y)
                    counts[k] = counts.get(k, 0) + 1
                    examples.setdefault(k, f'{a.iat[0, j]}: {x} -> {y}')
        if counts:
            parts.append(f'{sheet} ' + ', '.join(f'{n} {k} (e.g. {examples[k]})' for k, n in counts.items()))
        else:
            parts.append(f'{sheet} same')
    print(f'{d.name}: ' + '; '.join(parts))
