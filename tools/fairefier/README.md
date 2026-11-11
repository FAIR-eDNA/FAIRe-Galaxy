# FAIRe-fier Galaxy wrapper and command-line version

One Galaxy tool (`fairefier`) that checks a FAIRe workbook's projectMetadata and sampleMetadata
against the FAIRe checklist, using CSIRO's FAIRe-fier validation code. FAIRe-fier only exists as a
Shiny web app, so this folder also contains a **command-line version**, `fairefier_cli.py`, written
so it can be offered back to FAIRe-fier as a pull request.

Upstream: [csiro/FAIRe-fier](https://github.com/csiro/FAIRe-fier) at commit `183505d`
(30 Jun 2026, the latest on `main` as of 3 Nov 2026). BSD 3-Clause licence. Author: Suk Yee Yong.

## Status

- `planemo lint`: passes with no warnings. `pyflakes`: clean.
- `planemo test`: all 6 tests pass in Galaxy 25.0 (summary at the end of this file).
- **Same results as the web app.** The outputs were compared cell by cell, including every
  highlight colour, with the app's own Shiny code run headlessly (see "How equivalence was
  checked" below). Six cases, all identical.

## Files

| File | Purpose |
|---|---|
| `fairefier.xml` | Galaxy tool definition |
| `fairefier_cli.py` | Command-line version (new; see below) |
| `create_validator.py`, `config_data.py` | Upstream validation rules and settings, copied unchanged |
| `checklist/FAIRe_checklist_v1.0.xlsx` | Checklist shipped with FAIRe-fier |
| `checklist/FAIRe_checklist_v1.0.2.xlsx` | Current FAIRe checklist (as bundled with FAIRe-ator) |
| `checklist/LICENSE` | The FAIRe checklist's CC BY 4.0 licence (added upstream on 11 November 2026) |
| `LICENSE.upstream` | Upstream BSD 3-Clause licence |
| `test-data/` | Test workbooks (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder. `fairefier_cli.py` is derived from FAIRe-fier's own code and keeps its BSD 3-Clause licence (`LICENSE.upstream`), as do the upstream files |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

The equivalence check is in `dev/fairefier_equivalence/` at the top of the repository, outside the
tool folder, so it is not published to the ToolShed.

## The command-line version

```bash
python fairefier_cli.py WORKBOOK.xlsx -o OUTDIR [--checklist_version auto|v1.0|v1.0.2] [--checklist_dir DIR] [--strict]
```

It writes the same two workbooks as the app's download buttons:

- `fairefier_metadata.xlsx` when the worksheets pass;
- `fairefier_warn_error.xlsx` when there are warnings or errors, with `_revise` copies of the
  worksheets and the problem cells highlighted.

It also writes two files for scripts and pipelines, including the planned AI-assisted mapper:

- `fairefier_issues.tsv`: one row per warning or error (worksheet, level, record, term, input,
  type, message, suggested value);
- `fairefier_summary.json`: pass or fail for each worksheet, error and warning counts, the
  checklist version used and the app's validation message.

The exit status is 0 when validation ran (pass or fail), 2 when the workbook could not be read
(for example duplicate sample names), and 1 with `--strict` when validation fails.

**How it is built.** The validation rules (`create_validator.py`) are imported unchanged. The code
that runs them, groups the messages and writes the workbooks is taken line for line from the Shiny
server in `validate_module.py`, with the Shiny reactive values replaced by function arguments.
Three things are added: the plain-text outputs, a choice of checklist (by default the version in
`checkls_ver`), and a reset of Python's warning settings (see "Upstream issues").

### How equivalence was checked

`dev/fairefier_equivalence/run_shiny_reference.py` runs the unchanged `validate_module.py` with a
stand-in for Shiny, calls the same functions as the app's Submit and Download buttons, and saves the
downloads. `compare_outputs.py` then compares them with the command-line outputs: sheet names,
every cell value and every cell fill colour. `check.sh` runs both for any workbook.

| Case | Checklist | Result |
|---|---|---|
| GOMECC-4 generic FAIRe example (502 samples, 2,909 issues) | v1.0 and v1.0.2 | identical |
| Valid workbook from a FAIRe-ator template | v1.0.2 | identical |
| Invalid workbook (3 errors, 2 warnings) | v1.0 and v1.0.2 | identical |
| Re-submitted `_revise` workbook | v1.0.2 | identical |
| Duplicate sample names | v1.0.2 | same message; both stop |

These comparisons were run with warnings silenced as Galaxy silences them, and with a fixed
`PYTHONHASHSEED` because upstream orders some warnings by set iteration (see below).

## Upstream issues to report

To Suk Yee Yong (FAIRe-fier). Sent 5 November 2026; her answers of 5 and 6 November are noted
under each item.

1. **No command-line or library interface.** Offer `fairefier_cli.py` as a pull request. Ideally
   `validate_module.py` would then call its functions (`read_worksheets`, `run_validator`,
   `write_metadata`, `write_warn_error`), so the app and the command line cannot drift apart.
   *Answer:* the command-line script is welcome as a pull request (opened by Oliver on 7 November
   from the `command-line` branch of `ollybolly/FAIRe-fier`, with a reply to her email). The hosted web
   app is separate from the public repository and is updated in two steps, so the Galaxy tool
   follows the public repository. Suk Yee offered to have the public-repository app hosted
   elsewhere, so the app, command line and scripts would share one code base and package
   versions; whoever hosts it would then maintain it. Not yet decided.
2. **Warnings disappear when Python warnings are silenced.** Warnings such as "Closest option
   found" are collected with `warnings.catch_warnings(record=True)` without setting a filter, so
   any environment with `PYTHONWARNINGS=ignore` loses them. Galaxy sets exactly that for every
   job. The command-line version restores Python's standard filters; upstream could add
   `warnings.simplefilter('always')` inside each `catch_warnings` block. *Answer:* will be added.
3. **Extra-term warnings come out in a different order on each run**, because `warn_exterm` loops
   over a Python set. Sorting the set would make outputs reproducible. *Answer:* will be added.
4. **Dates stored as Excel dates fail.** For example `mod_date` in the NOAA example is reported as
   an error. The help text tells users to format cells as text; converting dates would be kinder.
   *Answer:* FAIRe-fier will keep asking for dates as text, as other ways of stopping Excel's
   conversion were not reliable. The fix belongs in the templates: their date columns should be
   formatted as text. They are General in FAIRe-ator's templates and the checklist's full
   template, which Oliver raised with Miwa Takahashi on 6 November.
5. `config_data.py` reads the checklists from the current folder when imported and uses
   `glob.glob1`, which is deprecated in recent Python. Taking the folder as a setting would help.
6. The bundled checklist is v1.0. FAIRe-ator and the FAIRe checklist repository are at v1.0.2,
   which differs in the allowed values for `filter_material` and `checksum_method`. *Answer:* the
   updated checklist will be added to the app.
7. Requirements pin `pydantic==2.7.0` (April 2024). Moving to a current version may change error
   wording, which the tests here would show.

To the FAIRe checklist and FAIRe-ator authors:

8. **`checkls_ver` is inconsistent between the tools.** The checklist defines it as a number
   (example `1.2`; the NOAA example uses `1`). FAIRe-ator fills it with the file name
   `FAIRe_checklist_v1.0.2.xlsx`, which FAIRe-fier reports as an error. So every unedited
   FAIRe-ator template fails FAIRe-fier. A version such as `1.0.2` also fails as a number. The
   field needs to become text (for example `v1.0.2`), or FAIRe-ator needs to write a number. The
   Galaxy tool reads either form when choosing a checklist, and its help tells users about the
   error.

## Before deployment on Galaxy Australia

### Must do

1. **Share the command-line version with Suk Yee Yong** and agree how it should live upstream.
   Once upstream has a command-line interface and a tagged release, the wrapper can use it
   directly, and the copied code here can go.
2. **Settle `checkls_ver`** with the FAIRe checklist and FAIRe-ator authors (issue 8). Until then,
   every FAIRe-ator template shows one error.
3. **Test with real Australian workbooks** and compare with the hosted app at
   shiny.csiro.au/FAIRe-fier, ideally with people who already use it.
4. **Fill in `.shed.yml`** and add the wrapper maintainers to the `<creator>` block, then publish
   to the Test ToolShed and main ToolShed, and ask Galaxy Australia to install it.

### Should do

5. **Package FAIRe-fier for pip and bioconda** once it has a command-line entry point. The IUC
   expects tools to come from a conda package.
6. **Plan checklist updates.** New FAIRe checklist versions go into `checklist/` and the version
   list in `fairefier.xml`.
7. **Use it in workflows.** The `--strict` option ("Stop with an error if validation fails")
   lets a Galaxy workflow stop before the ENA, NCBI or OBIS steps when metadata are invalid. The
   summary and issues table are what the mapper's validation loop will read.

## Test data

All made up, built from a mandatory-fields-only FAIRe-ator template (water, metabarcoding, one
assay, MiFish) by `dev/fairefier_equivalence/make_fairefier_testdata.py`:

- `faire_valid.xlsx`: two seawater samples and a field negative control at Rottnest Island;
  passes. `checkls_ver` is set to 1, as in the NOAA example.
- `faire_invalid.xlsx`: the same with five problems: `checkls_ver` as FAIRe-ator writes it, a
  misspelt sample category, a date in dd/mm/yyyy form, an ENVO term without its ID, and a latitude
  with too few decimal places.
- `faire_revise.xlsx`: the `fairefier_warn_error` workbook from the invalid run, to test
  re-submission.
- `faire_duplicate.xlsx`: the valid workbook with a repeated sample name.

## Running the tests

```bash
pip install planemo
planemo lint fairefier/
planemo test fairefier/     # run as an ordinary user, not root
```

## planemo test results

Run on 3 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (python 3.12, pandas 2.2.3, openpyxl 3.1.5, pydantic 2.7.0, jinja2 3.1.6).
All tests passed.

| Test | Checks | Result |
|---|---|---|
| 1 | Valid workbook: passes, checklist v1.0.2 chosen, no issues, validated workbook written | passed |
| 2 | Invalid workbook: fails, version read from checkls_ver, 5 issues with expected rows, highlighted workbook written | passed |
| 3 | Checklist v1.0 chosen by the user | passed |
| 4 | Re-submitted `_revise` workbook is read and checked | passed |
| 5 | Strict mode: job stops (exit 1) when validation fails | passed |
| 6 | Duplicate sample names: job stops (exit 2) with the app's message | passed |
