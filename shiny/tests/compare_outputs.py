"""Compares what the demonstration flows wrote with two versions of the app: each workbook sheet by sheet
(the values, as text, and the column names), FAIRe-fier's findings (in any order) and the Darwin Core
report. The README
sheet and the log, which hold times and file paths, are left out.

    python3 tests/compare_outputs.py BEFORE_DIR AFTER_DIR

Exits 1 if anything differs."""
import json
import sys
from pathlib import Path

import openpyxl

SKIP_SHEETS = {'README'}


def sheet_values(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        if ws.title in SKIP_SHEETS:
            continue
        out[ws.title] = [tuple('' if v is None else str(v) for v in row) for row in ws.iter_rows(values_only=True)]
    return out


def main(a, b):
    a, b = Path(a), Path(b)
    names = sorted({p.name for p in a.iterdir()} | {p.name for p in b.iterdir()})
    bad = 0
    for n in names:
        pa, pb = a / n, b / n
        if not (pa.exists() and pb.exists()):
            print(f'DIFFER {n}: only in {"the first" if pa.exists() else "the second"} folder')
            bad += 1
            continue
        if n.endswith('.xlsx'):
            va, vb = sheet_values(pa), sheet_values(pb)
            if va.keys() != vb.keys():
                print(f'DIFFER {n}: sheets {sorted(va)} and {sorted(vb)}')
                bad += 1
                continue
            for sh in va:
                if va[sh] != vb[sh]:
                    rows = [i for i, (x, y) in enumerate(zip(va[sh], vb[sh])) if x != y]
                    print(f'DIFFER {n} {sh}: {len(va[sh])} and {len(vb[sh])} rows; first differing rows {rows[:5]}')
                    bad += 1
            print(f'same   {n}: {len(va)} sheets, {sum(len(v) for v in va.values())} rows')
        elif n.endswith('.json'):
            same = json.loads(pa.read_text()) == json.loads(pb.read_text())
            print(('same  ' if same else 'DIFFER'), n)
            bad += not same
        elif n.endswith('.tsv'):
            # FAIRe-fier lists its findings in no set order: the same lines in any order are the same findings
            la, lb = pa.read_text().splitlines(), pb.read_text().splitlines()
            same = la[:1] == lb[:1] and sorted(la[1:]) == sorted(lb[1:])
            print(('same  ' if same else 'DIFFER'), n, '(lines in any order)')
            bad += not same
        else:
            same = pa.read_text() == pb.read_text()
            print(('same  ' if same else 'DIFFER'), n)
            bad += not same
    print('No differences' if not bad else f'{bad} differences')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
