"""Write tools/faire2ena/test-data/faire_ena_units.xlsx, for the tests of ENA's units and values.

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
"""
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_DATA = os.path.join(HERE, '..', '..', 'tools', 'faire2ena', 'test-data')

CHANGES = {
    'GOMECC4_27N_Sta1_DCM_A': {'samp_size': None, 'samp_size_unit': None, 'nitrate_unit': '\u00b5M',
                               'diss_inorg_carb_unit': 'mg/L'},
    'GOMECC4_27N_Sta1_DCM_B': {'samp_vol_we_dna_ext_unit': None, 'diss_oxygen': 0.193443,
                               'diss_oxygen_unit': 'mmol/kg'},
    'GOMECC4_BROWNSVILLE_Sta63_DCM_A': {'samp_store_temp': 'ambient temperature', 'samp_size': 2,
                                        'samp_size_unit': 'kg', 'nitrite_unit': '\u00b5mol/L',
                                        'nitrate_unit': None},
}


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


if __name__ == '__main__':
    main()
