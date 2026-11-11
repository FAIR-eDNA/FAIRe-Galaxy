"""Compare two FAIRe-fier output folders: sheet names, cell values and cell fill colours."""
import sys
from pathlib import Path
import openpyxl

a, b = Path(sys.argv[1]), Path(sys.argv[2])
ok = True
for name in ('fairefier_metadata.xlsx', 'fairefier_warn_error.xlsx'):
    fa, fb = a / name, b / name
    if fa.exists() != fb.exists():
        print(f"DIFF {name}: present in {'ref' if fa.exists() else 'cli'} only"); ok = False; continue
    if not fa.exists():
        continue
    wa, wb = openpyxl.load_workbook(fa), openpyxl.load_workbook(fb)
    if wa.sheetnames != wb.sheetnames:
        print(f"DIFF {name}: sheets {wa.sheetnames} vs {wb.sheetnames}"); ok = False; continue
    cells = fills = 0
    for s in wa.sheetnames:
        x, y = wa[s], wb[s]
        if (x.max_row, x.max_column) != (y.max_row, y.max_column):
            print(f"DIFF {name}/{s}: shape {(x.max_row, x.max_column)} vs {(y.max_row, y.max_column)}"); ok = False; continue
        for rx, ry in zip(x.iter_rows(), y.iter_rows()):
            for cx, cy in zip(rx, ry):
                cells += 1
                if cx.value != cy.value:
                    print(f"DIFF {name}/{s}!{cx.coordinate}: {cx.value!r} vs {cy.value!r}"); ok = False
                fx = cx.fill.fgColor.rgb if cx.fill and cx.fill.fill_type else None
                fy = cy.fill.fgColor.rgb if cy.fill and cy.fill.fill_type else None
                if fx: fills += 1
                if fx != fy:
                    print(f"DIFF {name}/{s}!{cx.coordinate} fill: {fx} vs {fy}"); ok = False
    print(f"{name}: {len(wa.sheetnames)} sheets, {cells} cells, {fills} highlighted cells compared")
ma, mb = (a / 'message.txt').read_text().strip(), None
print('IDENTICAL' if ok else 'DIFFERENT')
