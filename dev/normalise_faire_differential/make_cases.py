"""Write the named test cases for the normalise_faire.py differential check.

Usage: python3 make_cases.py OUTDIR

Every case is built from workbooks already in this repository's test data:
- P00 is FAIRe2NCBI's FAIRe-NOAA-layout test workbook, unchanged (cell-level check only: it has no
  seq_run_id, which upstream FAIRe2QIIME needs).
- P01 is FAIRe2QIIME's two-assay test workbook rewritten in the FAIRe-NOAA layout (each assayN
  header replaced by that column's assay_name). normalise_faire.py should pass it through unchanged,
  and upstream FAIRe2QIIME accepts it. P02 to P08 start from P01, each with one kind of awkward
  value in the sample and run sheets.
- N01 is P00 with associatedSequences 'NA' and 'N/A' in two runs, for FAIRe2NCBI's 'only runs not
  yet submitted' option (upstream FAIRe2BioSample treats literal NA and N/A there as not blank).
- L01 and L02 are FAIRe-ator-layout twins of P01 (the original two-assay test workbook), so
  normalising them should give back P01. L03 is a single-assay workbook (assay details in
  project_level), which normalise_faire.py is meant to rewrite.
"""
import datetime
import shutil
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
NCBI_NOAA = ROOT / 'tools/faire2ncbi/test-data/faire_noaa_layout.xlsx'
TWO_ASSAYS = ROOT / 'tools/faire2qiime/test-data/faire_two_assays.xlsx'
ANALYSIS = ROOT / 'tools/edna2obis/test-data/faire_noaa_analysis_sheets.xlsx'
SINGLE = ROOT / 'tools/faire2qiime/test-data/faire_single_assay.xlsx'
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)


def assay_name_row(pm):
    return next(r[0].row for r in pm.iter_rows(min_row=2) if r[2].value == 'assay_name')


def to_noaa(path):
    """The workbook with each assayN header replaced by its assay_name (the FAIRe-NOAA layout)."""
    wb = openpyxl.load_workbook(path)
    pm = wb['projectMetadata']
    row = assay_name_row(pm)
    for cell in pm[1]:
        if isinstance(cell.value, str) and cell.value.startswith('assay') and cell.value[5:].isdigit():
            cell.value = pm.cell(row=row, column=cell.column).value
    return wb


def header_map(ws, row=3):
    return {str(c.value).strip(): c.column for c in ws[row] if c.value is not None}


def free_columns(ws, n):
    """The last n named columns of a sheet: optional fields that the cases can overwrite."""
    cols = sorted(header_map(ws).items(), key=lambda kv: kv[1])
    keep = {'samp_name', 'lib_id', 'assay_name', 'seq_run_id', 'filename', 'filename2', 'samp_category'}
    return [c for name, c in cols if name not in keep][-n:]


def put(ws, row, col, value, as_text=False):
    cell = ws.cell(row=row, column=col)
    cell.value = value
    if as_text:
        cell.data_type = 's'  # keep a leading '=' as text, as Excel does when a cell is formatted as text


def data_rows(ws):
    return sum(1 for r in ws.iter_rows(min_row=4, max_col=1, values_only=True) if r[0] is not None)


def variant(name, values_by_column, run_values=None):
    """values_by_column: {sampleMetadata field: [values]}. The fields are ones FAIRe2NCBI's BioSample table
    and FAIRe2QIIME's metadata table both carry, so the downstream checks see them."""
    wb = to_noaa(TWO_ASSAYS)
    ws = wb['sampleMetadata']
    cols = header_map(ws)
    for field, values in values_by_column.items():
        assert len(values) <= data_rows(ws), f'{name}: more values than samples in {field}'
        for i, (value, as_text) in enumerate(values):
            put(ws, 4 + i, cols[field], value, as_text)
    if run_values:
        er = wb['experimentRunMetadata']
        rcol = free_columns(er, 1)[0]
        for i, (value, as_text) in enumerate(run_values):
            put(er, 4 + i, rcol, value, as_text)
    wb.save(OUT / f'{name}.xlsx')


T = lambda v: (v, True)   # noqa: E731 - text cell
V = lambda v: (v, False)  # noqa: E731 - typed cell

shutil.copy(NCBI_NOAA, OUT / 'P00_ncbi_noaa_fixture.xlsx')
to_noaa(TWO_ASSAYS).save(OUT / 'P01_noaa_layout.xlsx')
shutil.copy(ANALYSIS, OUT / 'P02_noaa_with_analysis_sheets.xlsx')
variant('P03_na_like_text', {'station_id': [T('NA'), T('N/A'), T('null'), T('nan')],
                             'line_id': [T('None'), T('#N/A'), T('n/a'), T('NULL')],
                             'env_medium': [T('NA')]},
        run_values=[T('NA'), T('N/A')])
variant('P04_text_starting_with_equals', {'serial_number': [T('=see notes'), T('=0.5')],
                                          'station_id': [T('=Sta1'), T('=Sta63')]})
variant('P05_escaped_control_character', {'serial_number': [T('Station_x000B_5'), T('tab\there')]})
variant('P06_dates_and_times', {'serial_number': [V(datetime.date(2022, 6, 13)), V(datetime.datetime(2022, 6, 13, 9, 30)),
                                                  V(datetime.time(10, 23)), T('2017-06')],
                                'station_id': [T('2017-06-13')]})
variant('P07_numbers_and_ids', {'serial_number': [V(5), V(0.1), V(1e-7), T('001')],
                                'line_id': [T('1e5'), V(123456789), V(True)]})
variant('P08_whitespace', {'station_id': [T(' leading'), T('trailing '), T('two\nlines'), T('  ')]})
wb = openpyxl.load_workbook(NCBI_NOAA)
er = wb['experimentRunMetadata']
col = header_map(er)['associatedSequences']
put(er, 4, col, 'NA', True)
put(er, 5, col, 'N/A', True)
wb.save(OUT / 'N01_associated_sequences_na.xlsx')
shutil.copy(TWO_ASSAYS, OUT / 'L01_faire_twin.xlsx')
wb = openpyxl.load_workbook(TWO_ASSAYS)
pm = wb['projectMetadata']
col = next(c.column for c in pm[1] if c.value == 'assay2')
pm.cell(row=assay_name_row(pm), column=col).value = 'SSU18Sv9_EMP'   # differs only in case and punctuation
wb.save(OUT / 'L02_faire_twin_spelling.xlsx')
shutil.copy(SINGLE, OUT / 'L03_single_assay.xlsx')
print('cases written to', OUT)
