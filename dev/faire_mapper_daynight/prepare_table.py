"""Prepare the day-night sample sheet (West et al. 2024) for the FAIRe mapper.

Usage: python prepare_table.py SAMPLE_SHEET.xlsx OUT.xlsx

The sheet is used as published (its Excel time and date cells, and the latitudes stored as text with
non-breaking spaces, are kept), except for three changes a person would make before mapping:

1. The second '8B' (the row between 9A and 9C, Waubs Bay, 14 March 2022 10:00) is renamed 9B. Both
   OTU tables have a 9B column and no second 8B, so this is taken to be a typing slip.
2. A 'Sample type' column (sample or negative control) and a 'Control type' column are added. The
   sheet marks its six filtration controls only by name ('Filtration control 1 + 2'): Milli-Q rinse
   water filtered on site between the day and night intervals (methods, section 2.1).
3. A row is added for the extraction blank Extbl19_4, which the 16S OTU table holds but the sheet
   does not (an extraction blank was processed with every set of 23 samples; section 2.2).

The notes in 'Collected by', 'Filtered by' and 'Information:' (lists of people and a short ReadMe in
the first rows) are left as they are; the review deletes or leaves them out.
"""
import sys

import openpyxl

src, out = sys.argv[1:3]
wb = openpyxl.load_workbook(src)
ws = wb.active
header = [c.value for c in ws[1]]
col = {name: i + 1 for i, name in enumerate(header)}
ids = [(r, str(ws.cell(r, col['Sample ID']).value)) for r in range(2, ws.max_row + 1)]
eights = [r for r, v in ids if v == '8B']
if len(eights) != 2:
    raise SystemExit(f'expected 8B twice, found it {len(eights)} times')
second = eights[1]
if (ws.cell(second - 1, col['Sample ID']).value, ws.cell(second + 1, col['Sample ID']).value) != ('9A', '9C'):
    raise SystemExit('the second 8B is not between 9A and 9C')
ws.cell(second, col['Sample ID']).value = '9B'

type_col, control_col = ws.max_column + 1, ws.max_column + 2
ws.cell(1, type_col).value, ws.cell(1, control_col).value = 'Sample type', 'Control type'
controls = 0
for r, v in ids:
    control = v.startswith('Filtration control')
    controls += control
    ws.cell(r, type_col).value = 'negative control' if control else 'sample'
    ws.cell(r, control_col).value = 'field negative' if control else None
blank = ws.max_row + 1
ws.cell(blank, col['Sample ID']).value = 'Extbl19_4'
ws.cell(blank, type_col).value, ws.cell(blank, control_col).value = 'negative control', 'extraction negative'
wb.save(out)
print(f'{blank - 1} rows: 9B renamed from the second 8B; {controls} filtration controls and one extraction '
      'blank marked as negative controls')
