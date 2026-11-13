"""Write a reviewer's decisions into a copy of a FAIRe mapper review sheet, as a person would in Excel.

Usage: python fill_review_sheet.py REVIEW_SHEET DECISIONS_TSV OUT

DECISIONS_TSV has the columns input, decision (Accept, Reject, Change or empty) and replacement. Each row
of the Review sheet takes the decision and replacement given for its input term; rows not in the file
keep what they have. Everything else in the sheet (the drop-downs, shading and the other sheets) is kept.
"""
import csv
import sys

from openpyxl import load_workbook


def main(sheet, decisions, out):
    with open(decisions, encoding='utf-8', newline='') as f:
        given = {r['input'].strip(): r for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)}
    wb = load_workbook(sheet)
    ws = wb['Review']
    head = [str(c.value or '').strip() for c in ws[1]]
    col_input, col_decision, col_replacement = (
        head.index(h) + 1 for h in ('Input term', "Reviewer's decision", 'Replacement FAIRe term'))
    n = 0
    for r in range(2, ws.max_row + 1):
        d = given.get(str(ws.cell(r, col_input).value or '').strip())
        if d is None:
            continue
        ws.cell(r, col_decision).value = d['decision'].strip() or None
        ws.cell(r, col_replacement).value = d['replacement'].strip() or None
        n += 1
    wb.save(out)
    print(f'{n} decisions written to the review sheet')


if __name__ == '__main__':
    main(*sys.argv[1:4])
