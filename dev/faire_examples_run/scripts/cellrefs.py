"""Print the first cell reference and value for (sheet, term) pairs in a workbook (read-only)."""
import sys
import warnings

import openpyxl

warnings.simplefilter('ignore')
path = sys.argv[1]
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
for spec in sys.argv[2:]:
    sheet, term = spec.split(':', 1)
    ws = wb[sheet]
    rows = list(ws.iter_rows())
    if sheet == 'projectMetadata':
        hdr = [c.value for c in rows[0]]
        t = hdr.index('term_name')
        for r in rows:
            if r[t].value == term:
                print(spec, [(c.coordinate, c.value) for c in r[t + 1:] if c.value is not None][:5])
                break
        else:
            print(spec, 'absent')
    else:
        hdr = [c.value for c in rows[2]]
        if term not in hdr:
            print(spec, 'absent')
            continue
        j = hdr.index(term)
        vals = [(r[j].coordinate, r[j].value) for r in rows[3:] if len(r) > j and r[j].value is not None]
        print(spec, f"{len(vals)} cells, first {vals[0] if vals else None}, last {vals[-1] if vals else None}")
