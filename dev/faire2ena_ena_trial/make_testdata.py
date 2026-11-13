"""Write tools/faire2ena/test-data/faire_ena_units.xlsx, for the tests of ENA's units and values, and
faire_single_end.xlsx, for the test of single-end runs.

Usage: python make_testdata.py

Starts from tools/faire2ena/test-data/faire_two_assays.xlsx and changes three samples, as the ENA
test-server trial of 11 November 2026 showed (README.md):

- GOMECC4_27N_Sta1_DCM_A: samp_size and samp_size_unit empty (left out, not written as "Unknown");
- GOMECC4_27N_Sta1_DCM_B: samp_vol_we_dna_ext_unit empty (the extraction volume is left out);
- GOMECC4_BROWNSVILLE_Sta63_DCM_A: samp_store_temp "ambient temperature" (not a number, so left
  out) and samp_size 2 kg (kept in kg, one of ENA's units).

and, for the chemistry fields (12 November 2026), units ENA can take after converting:

- GOMECC4_27N_Sta1_DCM_A: nitrate 0 µM (0 µmol/L); diss_inorg_carb 2033.19 mg/L (2033190 µg/L);
- GOMECC4_27N_Sta1_DCM_B: diss_oxygen 0.193443 mmol/kg (193.443 µmol/kg);
- GOMECC4_BROWNSVILLE_Sta63_DCM_A: nitrite 0.00878 µmol/L (kept), nitrate with no unit (left out).

and, for the size-fraction fields (12 November 2026):

- GOMECC4_27N_Sta1_DCM_A: size_frac_low 20 (a 20 µm pre-filter: ENA's size-fraction upper threshold).

and, for the collection date (13 November 2026):

- GOMECC4_BROWNSVILLE_Sta63_DCM_A: eventDate 2021-10-02T14:27+09:30, an offset with minutes, which
  ENA's date pattern cannot hold (it takes whole hours, +10), so it is written in UTC.

faire_single_end.xlsx is faire_two_assays.xlsx with lib_layout 'single end' and the reverse-read file
and checksum taken out of the ssu16sv4v5-emp rows; the ssu18sv9-emp rows keep theirs, so that a run
of that assay shows the check for a second file in a single-end library.
"""
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_DATA = os.path.join(HERE, '..', '..', 'tools', 'faire2ena', 'test-data')

CHANGES = {
    'GOMECC4_27N_Sta1_DCM_A': {'samp_size': None, 'samp_size_unit': None, 'nitrate_unit': '\u00b5M',
                               'diss_inorg_carb_unit': 'mg/L', 'size_frac_low': 20},
    'GOMECC4_27N_Sta1_DCM_B': {'samp_vol_we_dna_ext_unit': None, 'diss_oxygen': 0.193443,
                               'diss_oxygen_unit': 'mmol/kg'},
    'GOMECC4_BROWNSVILLE_Sta63_DCM_A': {'samp_store_temp': 'ambient temperature', 'samp_size': 2,
                                        'samp_size_unit': 'kg', 'nitrite_unit': '\u00b5mol/L',
                                        'nitrate_unit': None, 'eventDate': '2021-10-02T14:27+09:30'},
}


def header_row(ws, first):
    """The row of field names (the one whose first cell is first) and {name: column}."""
    header = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == first)
    return header, {ws.cell(header, c).value: c for c in range(1, ws.max_column + 1)}


def single_end():
    wb = openpyxl.load_workbook(os.path.join(TEST_DATA, 'faire_two_assays.xlsx'))
    ws = wb['projectMetadata']
    _, columns = header_row(ws, 'requirement_level_code')
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, columns['term_name']).value == 'lib_layout')
    ws.cell(row, columns['project_level']).value = 'single end'
    ws = wb['experimentRunMetadata']
    header, columns = header_row(ws, 'samp_name')
    cleared = 0
    for r in range(header + 1, ws.max_row + 1):
        if ws.cell(r, columns['assay_name']).value == 'ssu16sv4v5-emp':
            ws.cell(r, columns['filename2']).value = None
            ws.cell(r, columns['checksum_filename2']).value = None
            cleared += 1
    if not cleared:
        raise SystemExit('no ssu16sv4v5-emp rows in experimentRunMetadata')
    wb.save(os.path.join(TEST_DATA, 'faire_single_end.xlsx'))


def main():
    wb = openpyxl.load_workbook(os.path.join(TEST_DATA, 'faire_two_assays.xlsx'))
    ws = wb['sampleMetadata']
    header = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == 'samp_name')
    columns = {ws.cell(header, c).value: c for c in range(1, ws.max_column + 1)}
    done = set()
    for r in range(header + 1, ws.max_row + 1):
        name = ws.cell(r, 1).value
        for term, value in CHANGES.get(name, {}).items():
            ws.cell(r, columns[term]).value = value
            done.add(name)
    if done != set(CHANGES):
        raise SystemExit(f'samples not found: {sorted(set(CHANGES) - done)}')
    wb.save(os.path.join(TEST_DATA, 'faire_ena_units.xlsx'))
    single_end()


if __name__ == '__main__':
    main()
