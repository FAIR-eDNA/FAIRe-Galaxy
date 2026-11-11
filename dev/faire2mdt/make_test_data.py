"""Write the FAIRe2MDT Galaxy tool's test data (tools/faire2mdt/test-data).

All values are made up for the tests. The workbook has two assays whose names overlap (MiFish and
MiFish-E) and two runs whose names overlap (run1 and run10), Excel date and time cells, and a
number that Excel stores with more digits than it shows (105.70852).

Usage: python make_test_data.py [OUTPUT_DIR]
"""
import csv
import datetime as dt
import sys
import zipfile
from pathlib import Path

import openpyxl

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / 'tools' / 'faire2mdt' / 'test-data'
out.mkdir(parents=True, exist_ok=True)


def sheet(wb, name, rows):
    ws = wb.create_sheet(name)
    for r in rows:
        ws.append(list(r))
    return ws


def date_cells(ws, fmt):
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, (dt.datetime, dt.date, dt.time)):
                c.number_format = fmt if not isinstance(c.value, dt.time) else 'hh:mm'


ASVS = {
    'ASV_1': ('ACACCGCCCGTCACTCTCCCCAAG', 'Animalia', 'Chordata', 'Teleostei', 'Perciformes', 'Sparidae', 'Pagrus', 'Pagrus auratus'),
    'ASV_2': ('ACACCGCCCGTCACCCTCCTCAAA', 'Animalia', 'Chordata', 'Teleostei', 'Labriformes', 'Labridae', 'Choerodon', None),
    'ASV_3': ('ACACCGCCCGTCACCCTTCTCAAG', 'Animalia', 'Chordata', 'Teleostei', None, None, None, None),
}
TAXA_HEAD = [['# requirement_level_code', 'M', 'M', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O'],
             ['# section', 'OTU/ASV'] + ['Taxonomy'] * 9,
             ['seq_id', 'dna_sequence', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus',
              'scientificName', 'percent_match', 'notes']]


def taxa_rows(ids):
    return TAXA_HEAD + [[i, *ASVS[i], 99.5, None] for i in ids]


wb = openpyxl.Workbook()
wb.remove(wb.active)
sheet(wb, 'README', [['Test data made for the FAIRe2MDT Galaxy tool. All values are made up.']])
pm = sheet(wb, 'projectMetadata', [
    ['requirement_level_code', 'section', 'term_name', 'project_level', 'assay1', 'assay2'],
    ['M', 'Project', 'project_id', 'mdttest', None, None],
    ['M', 'Project', 'project_name', 'Test data for the FAIRe2MDT Galaxy tool', None, None],
    ['M', 'Project', 'checkls_ver', 'v1.0.2', None, None],
    ['O', 'Project', 'mod_date', dt.datetime(2026, 11, 3), None, None],
    ['M', 'PCR', 'assay_name', 'MiFish | MiFish-E', 'MiFish', 'MiFish-E'],
    ['M', 'PCR', 'target_gene', None, '12S rRNA (SSU mitochondria)', '12S rRNA (SSU mitochondria)'],
    ['M', 'PCR', 'pcr_primer_forward', None, 'GTCGGTAAAACTCGTGCCAGC', 'GTTGGTAAATCTCGTGCCAGC'],
    ['HR', 'PCR', 'ampliconSize', None, 170, 172],
])
date_cells(pm, 'yyyy-mm-dd')
sm = sheet(wb, 'sampleMetadata', [
    ['# requirement_level_code', 'M', 'M', 'M', 'M', 'HR', 'O', 'R', 'R', 'O'],
    ['# section', 'Sample information'] + ['Sample collection'] * 8,
    ['samp_name', 'samp_category', 'decimalLatitude', 'decimalLongitude', 'eventDate', 'verbatimEventTime',
     'samp_size', 'samp_size_unit', 'env_medium', 'samp_store_sol'],
    ['S1', 'sample', -10.54138, 105.70852, dt.datetime(2024, 3, 5), dt.time(9, 25), 2, 'L', 'sea water [ENVO:00002149]', None],
    ['S2', 'sample', -10.6, 105.8, dt.datetime(2024, 3, 6), dt.time(10, 5), 2, 'L', 'sea water [ENVO:00002149]', None],
    ['S3', 'sample', -10.7, 105.9, dt.datetime(2024, 3, 7), dt.time(11, 40), 2, 'L', 'sea water [ENVO:00002149]', None],
    ['NC1', 'negative control', None, None, 'missing: not collected', None, 2, 'L', None, None],
])
date_cells(sm, 'yyyy-mm-dd')
sheet(wb, 'experimentRunMetadata', [
    ['# requirement_level_code', 'M', 'M', 'M', 'M', 'O'],
    ['# section', 'PCR', 'Library preparation sequencing', 'Library preparation sequencing',
     'Library preparation sequencing', 'Bioinformatics'],
    ['samp_name', 'assay_name', 'lib_id', 'seq_run_id', 'filename', 'input_read_count'],
    ['S1', 'MiFish', 'lib_S1_MiFish_run1', 'run1', 'S1_MiFish_R1.fastq.gz', 1000],
    ['S2', 'MiFish', 'lib_S2_MiFish_run1', 'run1', 'S2_MiFish_R1.fastq.gz', 1200],
    ['NC1', 'MiFish', 'lib_NC1_MiFish_run1', 'run1', 'NC1_MiFish_R1.fastq.gz', 10],
    ['S1', 'MiFish-E', 'lib_S1_MiFishE_run1', 'run1', 'S1_MiFishE_R1.fastq.gz', 900],
    ['S2', 'MiFish-E', 'lib_S2_MiFishE_run1', 'run1', 'S2_MiFishE_R1.fastq.gz', 950],
    ['S3', 'MiFish', 'lib_S3_MiFish_run10', 'run10', 'S3_MiFish_R1.fastq.gz', 800],
    ['S3', 'MiFish-E', 'lib_S3_MiFishE_run10', 'run10', 'S3_MiFishE_R1.fastq.gz', 700],
])
sheet(wb, 'otuFinal_MiFish-E_run1', [['seq_id', 'S1', 'S2'], ['ASV_1', 50, 0], ['ASV_3', 7, 31]])
sheet(wb, 'taxaFinal_MiFish-E_run1', taxa_rows(['ASV_1', 'ASV_3']))
wb.save(out / 'mdt_workbook.xlsx')
# Excel writes numbers with 17 significant digits (105.70851999999999 for 105.70852); openpyxl
# writes the shortest form, so put Excel's form back in the sheet XML.
with zipfile.ZipFile(out / 'mdt_workbook.xlsx') as z:
    parts = {i: z.read(i.filename) for i in z.infolist()}
with zipfile.ZipFile(out / 'mdt_workbook.xlsx', 'w', zipfile.ZIP_DEFLATED) as z:
    for info, data in parts.items():
        if info.filename == 'xl/worksheets/sheet3.xml':
            assert b'<v>105.70852</v>' in data
            data = data.replace(b'<v>105.70852</v>', b'<v>105.70851999999999</v>')
        z.writestr(info, data)

# MiFish, run1: OTU table as a separate workbook, taxonomy as TSV
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'otuFinal'
for r in [['seq_id', 'S1', 'S2', 'NC1'], ['ASV_1', 120, 3, 0], ['ASV_2', 0, 45, 0], ['ASV_3', 12, 0, 1]]:
    ws.append(r)
wb.save(out / 'otuFinal_mdttest_MiFish_run1.xlsx')
with open(out / 'taxaFinal_mdttest_MiFish_run1.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for r in taxa_rows(['ASV_1', 'ASV_2', 'ASV_3']):
        w.writerow(['' if v is None else v for v in r])

# MiFish, run1 again: OTU table as CSV with an empty cell and a column that is not a sample of this run (S9),
# taxonomy as a workbook whose only sheet has another name
with open(out / 'otuFinal_mdttest_MiFish_run1.csv', 'w', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    for r in [['seq_id', 'S1', 'S2', 'NC1', 'S9'], ['ASV_1', 120, 3, 0, 4], ['ASV_2', '', 45, 0, 0], ['ASV_3', 12, 0, 1, 0]]:
        w.writerow(r)
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Sheet1'
for r in taxa_rows(['ASV_1', 'ASV_2', 'ASV_3']):
    ws.append(r)
wb.save(out / 'taxa_one_sheet.xlsx')

# FAIRe's final tables: taxaFinal lists every ASV of a taxon, and otuFinal sums the taxon's reads under
# its most abundant ASV, so ASV_4 (Pagrus auratus, summed under ASV_1) has no otuFinal row
with open(out / 'taxaFinal_extra_asv.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    rows = taxa_rows(['ASV_1', 'ASV_2', 'ASV_3']) + [
        ['ASV_4', 'ACACCGCCCGTCACTCTCCCCAGG', *ASVS['ASV_1'][1:], 99.0,
         'reads summed in otuFinal under ASV_1, the most abundant ASV of Pagrus auratus']]
    for r in rows:
        w.writerow(['' if v is None else v for v in r])
print(f'wrote test data to {out}')
