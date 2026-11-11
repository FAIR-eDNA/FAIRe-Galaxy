"""Print raw openpyxl cell values and types for given terms in projectMetadata (read-only).
usage: cells.py WORKBOOK SHEET TERM [TERM ...]
For projectMetadata, TERM matches the term_name column (C). For other sheets, TERM matches row 3
and the first 5 data rows are shown."""
import sys
import warnings
import openpyxl

warnings.simplefilter('ignore')
path, sheet, *terms = sys.argv[1:]
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
ws = wb[sheet]
rows = list(ws.iter_rows(values_only=False))
if sheet == 'projectMetadata':
    hdr = [c.value for c in rows[0]]
    tcol = hdr.index('term_name')
    for r in rows:
        if r[tcol].value in terms:
            print(r[tcol].value, [(c.coordinate, repr(c.value), c.data_type, c.number_format) for c in r[tcol + 1:] if c.value is not None])
else:
    hdr = [c.value for c in rows[2]]
    for t in terms:
        if t not in hdr:
            print(t, 'absent')
            continue
        j = hdr.index(t)
        vals = [(r[j].coordinate, repr(r[j].value), r[j].data_type, r[j].number_format) for r in rows[3:] if len(r) > j and r[j].value is not None]
        print(t, len(vals), vals[:6])
