# Tests for the FAIRe tools app

Run them from the `shiny` folder.

- **`test_journey.R`**: unit tests of the journey (`R/journey.R`): the next step and each step's status
  for every situation the app can be in, from no files to a workbook that passes, and for a FAIRe
  workbook of your own or a blank template. `Rscript tests/test_journey.R`.
- **`flows/`**: the three demonstrations (eelgrass, SEA-MES, khapra beetle) taken through the app
  in Shiny's test server, from loading the files to the workbook, FAIRe-fier and a Darwin Core
  archive, as a person would with the forms. Each prints PASS or FAIL for its checks and exits 1 on
  a failure. `Rscript tests/flows/eelgrass.R`. Set `FAIRE_PYTHON` to the Python with the tools'
  packages, and `FAIRE_TEST_OUT` to keep the workbooks and reports it writes.
- **`compare_outputs.py`**: compares the outputs of the flows from two versions of the app, sheet by
  sheet, to show that a change to the app's screens has not changed what the tools write:
  `python3 tests/compare_outputs.py BEFORE AFTER`.
- **`browser/journeys.py`**: the journeys through the app in a browser (Playwright and Google Chrome):
  a blank template; the eelgrass demonstration from loading to a workbook that passes, through an
  unsaved review, missing mandatory terms, moving back and forth, and a workbook out of date; a FAIRe
  workbook of your own; a targeted assay; a narrow screen; the keyboard; and statuses that do not
  rest on colour. Start the app on port 8765, then `python3 tests/browser/journeys.py`.
- **`browser/tour.py`**: screenshots at each stage of the eelgrass demonstration, for comparing two
  versions: `python3 tests/browser/tour.py OUT_DIR`.

Version 0.9.0 was tested this way: the three flows on 0.8.12 (commit c123241) and on 0.9.0 give the
same outputs, sheet by sheet.
