"""Make tools/faire_mapper/test-data/method_details_reviewed.xlsx: the review sheet find method details
writes for the SEA-MES methods, filled in as a person might, for the apply mapping test.

Usage: python make_testdata.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

tools = Path(__file__).resolve().parents[2] / 'tools' / 'faire_mapper'
with tempfile.TemporaryDirectory() as tmp:
    sheet = Path(tmp) / 'sheet.xlsx'
    subprocess.run([sys.executable, str(tools / 'faire_method_details.py'), str(tools / 'test-data' / 'method_details_seames.txt'),
                    '--checklist', str(tools / 'checklist' / 'FAIRe_checklist_v1.0.2.xlsx'),
                    '-o', str(Path(tmp) / 'p.tsv'), '--review_sheet', str(sheet)], check=True, stdout=subprocess.DEVNULL)
    wb = load_workbook(sheet)
    ws = wb['Method details']
    head = [c.value for c in ws[1]]
    ti, vi, di, yi = (head.index(h) for h in ('FAIRe term', 'Proposed value', "Reviewer's decision", 'Your value'))
    accepted = set()
    for row in ws.iter_rows(min_row=2):
        t, v = row[ti].value, row[vi].value
        if t == 'samp_store_temp':
            row[di].value = 'Reject'              # FAIRe's term for storage after filtering is prepped_samp_store_temp
        elif t == 'prepped_samp_store_temp':
            row[di].value = 'Accept'
        elif t == 'instrument' and v:
            row[di].value = 'Change'
            row[yi].value = 'Illumina NextSeq 2000'
        elif t in ('nucl_acid_ext_kit', 'pcr_cond', 'annealingTemp', 'pcr_cycles', 'platform', 'otu_db',
                   'tax_class_id_cutoff') and v and t not in accepted:
            row[di].value = 'Accept'
            accepted.add(t)
        elif t == 'tax_class_id_cutoff' and v:
            row[di].value = 'Reject'              # the species-level threshold
        elif t == 'pcr_rep' and not v:
            row[yi].value = '1'                   # a term the tool did not find, given by the person
    wb.save(tools / 'test-data' / 'method_details_reviewed.xlsx')
print('wrote', tools / 'test-data' / 'method_details_reviewed.xlsx')
