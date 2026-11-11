# FAIRe-ator Galaxy wrapper

One Galaxy tool (`faireator`) that makes a blank FAIRe metadata template (.xlsx) tailored to a
study's project ID, assay type, assay names, sample types and requirement levels. It has no input
datasets; everything comes from the tool form.

Upstream: [FAIR-eDNA/FAIRe-ator](https://github.com/FAIR-eDNA/FAIRe-ator) at commit `dcb9323`
(24 Sep 2026, the latest on `main` as of 3 Nov 2026). Bundled checklist: FAIRe v1.0.2 from
[FAIR-eDNA/FAIRe_checklist](https://github.com/FAIR-eDNA/FAIRe_checklist) at commit `061d8b6`.
Both are CC BY 4.0: the licence files were added upstream on 11 November 2026 (FAIRe-ator
`5f523a1`, FAIRe_checklist `70fd1ea`, which change nothing else) and are copied in here as
`LICENSE.upstream` and `checklist/LICENSE`.

## Status

- `planemo lint`: passes with no warnings.
- `planemo test`: all tests pass in Galaxy 25.0 (summary at the end of this file).
- Ran the upstream function directly for five combinations of options; all produced templates.
- Not yet checked that the templates open in Excel without a repair prompt (see below).

## Files

| File | Purpose |
|---|---|
| `faireator.xml` | Galaxy tool definition |
| `FAIReator.R` | Upstream script, copied unchanged |
| `checklist/FAIRe_checklist_v1.0.2.xlsx` | FAIRe checklist, copied unchanged |
| `checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx` | FAIRe full template, copied unchanged |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `LICENSE.upstream` | FAIRe-ator's CC BY 4.0 licence |
| `checklist/LICENSE` | The FAIRe checklist's CC BY 4.0 licence |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

## How the wrapper works

The tool writes a short R script from the form, which sources `FAIReator.R` and calls
`FAIReator()` with the user's choices. The checklist files are linked into the job's working
directory, where the function expects them. The finished workbook is moved to the Galaxy output.

Choices made in the wrapper:

1. **Mandatory fields are always included.** The form lets users add or leave out highly
   recommended, recommended and optional fields. Upstream allows mandatory fields to be dropped,
   which gives a template that cannot pass validation.
2. **Assay type "other" is not offered.** Upstream partly handles it, but the function stops with
   an error (the list of extra sheets is never set).
3. **All R packages come from conda,** including `here`, which the function loads but does not use.
   If any package were missing, the function would try `install.packages()` at run time, which
   fails on servers without internet access.
4. **"All sample types" is passed as the full list of seven types.** Upstream's own option for this
   ("other") crashes when combined with a targeted assay type and more than one assay. Listing the
   seven types gives exactly the same fields (checked: 141 sampleMetadata fields, same order), and
   also keeps the pre-filled assay_name row that "other" leaves out.
5. **Names are checked on the form.** Project ID, assay names and extra field names must be
   letters, digits, `_` or `-`, as FAIRe asks.

## Upstream issues to report

- **Dangling drawing references in the output.** Each sheet with comments refers to a
  `xl/drawings/drawingN.xml` part that is not in the file. pandas reads the workbook, but
  openpyxl cannot open it in full (`KeyError: There is no item named 'xl/drawings/drawing1.xml'`).
  This comes from how openxlsx writes comments and drop-downs. The FAIRe2QIIME wrapper now reads
  workbooks through pandas so it is not affected.
- Assay type "other" fails (item 2 above).
- `install.packages()` at run time, and `here` loaded but unused (item 3).
- Sample type "other" combined with a targeted assay type and more than one assay stops with
  `Column detected_notDetected doesn't exist`. With "other", the sampleMetadata columns are never
  named, so later steps cannot find them. The same cause leaves out the pre-filled `assay_name` row
  at the foot of sampleMetadata. The wrapper avoids this (item 4 above).
- The checklist version (v1.0.2) is fixed in the code, so a new checklist release needs a code
  change as well as new files.
- No tagged releases. The tool version is the commit date (`2026.09.24`).

## Before deployment on Galaxy Australia

### Must do

1. ~~**Add a licence file** to FAIRe-ator and FAIRe_checklist upstream, and copy it in.~~ Done
   11 November 2026 (CC BY 4.0). The wrapper itself is MIT (`LICENSE`, and `license="MIT"` on the
   `<tool>` element), as for the other tools.
2. **Open the templates in Excel, LibreOffice and Google Sheets.** Because of the dangling drawing
   references, check that each opens without a repair prompt and that the comments and drop-down
   lists show. Make one template for each assay type to check.
3. **Ask a few users to try it**, ideally people who have used FAIRe-ator in R, and compare the
   Galaxy template with one made in R using the same options.
4. **Fill in `.shed.yml`** and add the maintainers to the `<creator>` block, then publish to the
   Test ToolShed and the main ToolShed, and ask Galaxy Australia to install it.

### Should do

5. **Plan for checklist updates.** Each new FAIRe checklist release means new bundled files and a
   new tool version. If upstream reads the version from an argument, the wrapper could offer a
   choice of bundled versions.
6. **Consider letting users supply their own checklist.** FAIReSheets lets users add their own
   fields to the checklist itself. The same could be done here with an optional checklist input,
   once upstream accepts a checklist path.
7. **Package for bioconda** once there is a licence and a tagged release, ideally as part of an R
   package (FAIR-eDNA already has a FAIRe-r repository of helper functions).

## Tests

The tool has no input datasets, so there is no `test-data` folder. The tests check the contents of
the .xlsx file (a zip archive) directly: the sheet names in `xl/workbook.xml`, and field names,
assay names and README text in `xl/sharedStrings.xml`. The README sheet records the time the
template was made, so the files cannot be compared byte for byte.

## Running the tests

```bash
pip install planemo
planemo lint faireator/
planemo test faireator/
```

## planemo test results

Run on 3 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (r-base 4.4.3, r-readxl 1.6.0, r-openxlsx 4.2.9, r-dplyr 1.2.1,
r-rcolorbrewer 1.1_3, r-here 1.0.2). All tests passed.

| Test | Checks | Result |
|---|---|---|
| 1 | Metabarcoding, water and sediment, two assays, all levels: metabarcoding sheets, assay1 column, assay names, README settings | passed |
| 2 | Targeted, soil, one assay, mandatory and highly recommended only, extra fields: targeted sheets, no assay columns, extra fields present | passed |
| 3 | All sample types with two targeted assays (the case that crashes upstream): one detection column per assay | passed |
