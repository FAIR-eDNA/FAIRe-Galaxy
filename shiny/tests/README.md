# Tests for the FAIRe tools app

Run them from the `shiny` folder.

- **`flows/`**: the three demonstrations (eelgrass, SEA-MES, khapra beetle) taken through the app
  in Shiny's test server, from loading the files to the workbook, FAIRe-fier and a Darwin Core
  archive, as a person would with the forms. Each prints PASS or FAIL for its checks and exits 1 on
  a failure. `Rscript tests/flows/eelgrass.R`. Set `FAIRE_PYTHON` to the Python with the tools'
  packages, and `FAIRE_TEST_OUT` to keep the workbooks and reports it writes.
- **`compare_outputs.py`**: compares the outputs of the flows from two versions of the app, sheet by
  sheet, to show that a change to the app's screens has not changed what the tools write:
  `python3 tests/compare_outputs.py BEFORE AFTER`.
