"""Write the tool test workbooks for text values that the tools, or the upstream code they run, change.

Usage: python3 make_testdata.py

- tools/faire2ncbi/test-data/faire_noaa_text_values.xlsx: faire_noaa_layout.xlsx with
  - associatedSequences 'NA' and 'N/A' for both runs of GU190707-CTD13-310 (FAIRe2BioSample treats
    literal NA and N/A there as filled, so that sample and its runs are not new);
  - serial_number '=see notes' for GU190706-CTD11-220 (text starting with '=') and 'Bottle #3' for
    GU190707-CTD14-315 (a '#' inside a cell);
  - env_medium 'NA' for GU190707-CTD14-315 (FAIRe2BioSample reads NA in sampleMetadata as empty);
  - materialSampleID '001' to '005' as text (IDs that look like numbers).
- tools/faire2qiime/test-data/faire_text_values.xlsx: faire_two_assays.xlsx with serial_number
  '=see notes' and station_id 'Sta1 #2' for GOMECC4_27N_Sta1_DCM_A, and materialSampleID '001' to
  '004' as text.
- tools/faire2qiime/test-data/faire_same_gene_text_values.xlsx: faire_same_gene.xlsx (assays converted
  one at a time) with serial_number '=see notes' for GOMECC4_27N_Sta1_DCM_A.
- tools/edna2obis/test-data/faire_text_values.xlsx: faire_two_assays.xlsx with station_id '=Sta1'
  for GOMECC4_27N_Sta1_DCM_A and 'N/A' for GOMECC4_27N_Sta1_DCM_B, env_medium 'N/A' for
  GOMECC4_27N_Sta1_DCM_B, and materialSampleID '001' to '004' as text.
"""
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]


def header_map(ws, row=3):
    return {str(c.value).strip(): c.column for c in ws[row] if c.value is not None}


def text_cell(cell, value):
    cell.value = value
    cell.data_type = 's'  # a text cell, as Excel writes text typed into a cell formatted as text


def set_text(ws, key_field, key, field, value):
    cols = header_map(ws)
    rows = [r for r in range(4, ws.max_row + 1) if ws.cell(row=r, column=cols[key_field]).value == key]
    assert rows, f'{key} not found in {ws.title}'
    for r in rows:
        text_cell(ws.cell(row=r, column=cols[field]), value)


def number_ids(ws, field):
    """field = '001', '002', ... as text, for every sample row."""
    cols = header_map(ws)
    rows = [r for r in range(4, ws.max_row + 1) if ws.cell(row=r, column=cols['samp_name']).value not in (None, '')]
    for i, r in enumerate(rows, start=1):
        text_cell(ws.cell(row=r, column=cols[field]), f'{i:03d}')


wb = openpyxl.load_workbook(ROOT / 'tools/faire2ncbi/test-data/faire_noaa_layout.xlsx')
er = wb['experimentRunMetadata']
set_text(er, 'lib_id', 'GU190707-CTD13-310_MiFish_S31', 'associatedSequences', 'NA')
set_text(er, 'lib_id', 'GU190707-CTD13-310_Riaz_S2', 'associatedSequences', 'N/A')
sm = wb['sampleMetadata']
set_text(sm, 'samp_name', 'GU190706-CTD11-220', 'serial_number', '=see notes')
set_text(sm, 'samp_name', 'GU190707-CTD14-315', 'serial_number', 'Bottle #3')
set_text(sm, 'samp_name', 'GU190707-CTD14-315', 'env_medium', 'NA')
number_ids(sm, 'materialSampleID')
wb.save(ROOT / 'tools/faire2ncbi/test-data/faire_noaa_text_values.xlsx')

wb = openpyxl.load_workbook(ROOT / 'tools/faire2qiime/test-data/faire_two_assays.xlsx')
sm = wb['sampleMetadata']
set_text(sm, 'samp_name', 'GOMECC4_27N_Sta1_DCM_A', 'serial_number', '=see notes')
set_text(sm, 'samp_name', 'GOMECC4_27N_Sta1_DCM_A', 'station_id', 'Sta1 #2')
number_ids(sm, 'materialSampleID')
wb.save(ROOT / 'tools/faire2qiime/test-data/faire_text_values.xlsx')

wb = openpyxl.load_workbook(ROOT / 'tools/faire2qiime/test-data/faire_same_gene.xlsx')
set_text(wb['sampleMetadata'], 'samp_name', 'GOMECC4_27N_Sta1_DCM_A', 'serial_number', '=see notes')
wb.save(ROOT / 'tools/faire2qiime/test-data/faire_same_gene_text_values.xlsx')

wb = openpyxl.load_workbook(ROOT / 'tools/edna2obis/test-data/faire_two_assays.xlsx')
sm = wb['sampleMetadata']
set_text(sm, 'samp_name', 'GOMECC4_27N_Sta1_DCM_A', 'station_id', '=Sta1')
set_text(sm, 'samp_name', 'GOMECC4_27N_Sta1_DCM_B', 'station_id', 'N/A')
set_text(sm, 'samp_name', 'GOMECC4_27N_Sta1_DCM_B', 'env_medium', 'N/A')
number_ids(sm, 'materialSampleID')
wb.save(ROOT / 'tools/edna2obis/test-data/faire_text_values.xlsx')
print('test workbooks written')
