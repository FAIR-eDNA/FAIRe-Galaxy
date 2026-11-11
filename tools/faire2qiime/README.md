# FAIRe2QIIME Galaxy wrapper

One Galaxy tool (`faire2qiime`) that turns a FAIRe metadata workbook into:

- QIIME 2 sample metadata, one tabular file per assay (a Galaxy collection);
- optionally, QIIME 2 paired-end manifests, one per sequencing run and assay (a second collection);
- a log.

Upstream: [aomlomics/faire2qiime](https://github.com/aomlomics/faire2qiime) at commit `13e87de`
(23 Jul 2026, the latest on `main` as of 3 Nov 2026). CC0 licence.

## Status

- `planemo lint`: passes with no warnings.
- `planemo shed_lint`: passes except for the placeholder owner in `.shed.yml`.
- `planemo test`: all tests pass in Galaxy 25.0 (summary at the end of this file).
- Not yet tested with a workbook made by FAIRe-ator for an Australian project, or with QIIME 2
  itself.

## Files

| File | Purpose |
|---|---|
| `faire2qiime.xml` | Galaxy tool definition |
| `faire2qiime.py` | Upstream script, copied unchanged |
| `normalise_faire.py` | Galaxy step that runs before the upstream script (see below) |
| `faire2qiime_by_assay.py` | Galaxy step that runs the upstream script once for each assay when two assays share a target gene and subfragment (see below) |
| `faire2qiime_run.py` | Runs the upstream script with a reader that keeps the workbook's values as written (item 7) |
| `LICENSE.upstream` | Upstream CC0 licence |
| `test-data/` | Test workbooks (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

## What the wrapper adds

1. **Works with FAIRe-ator workbooks.** FAIRe2QIIME was written for the FAIRe-NOAA layout, in
   which each assay has a projectMetadata column headed by its assay name. The FAIRe checklist and
   FAIRe-ator use columns headed `assay1`, `assay2` ..., with the name in the `assay_name` row, or
   put a single assay's details in `project_level`. Upstream fails on these with
   `KeyError: '<assay name>'`. `normalise_faire.py` writes a copy of the workbook with the assay
   columns relabelled by assay name, then the upstream script runs on that copy. NOAA-layout
   workbooks pass through unchanged. The copy holds values only, which is all FAIRe2QIIME reads.
   Values are copied as they are: text such as `NA` stays text, and text starting with `=` stays
   text (openpyxl would otherwise save it as a formula with no value).
   It is read through pandas, because openpyxl cannot fully open workbooks written by FAIRe-ator
   (see the FAIRe-ator README).
2. **Column checks.** If the chosen sample ID column (or suffix column) does not exist, upstream
   stops with a bare `KeyError`. The wrapper stops with a plain message first.
3. **Collections.** Output file names depend on the data (project, gene, subfragment, run), so the
   tool gathers them into two Galaxy collections, named by the upstream file names.
4. **Manifests are optional.** Users who will import reads into QIIME 2 inside Galaxy do not need
   them.
5. **Tidy log.** The colour codes and the "install pyfiglet" tip are removed from the log.
6. **Checks added after running the FAIRe example workbooks** (3 November 2026):
   - assay names that differ only in punctuation or case between sheets (`12S-V5` in
     projectMetadata, `12S_V5` in experimentRunMetadata) are matched, with a warning; other
     mismatches stop with a plain message instead of a `KeyError`;
   - with manifests on, runs without a `filename` stop the tool (upstream writes paths ending in
     `nan`);
   - two assays with the same target_gene and target_subfragment are converted one at a time
     (`faire2qiime_by_assay.py`, since 6 November 2026), and every file is then named by its
     assay_name. Upstream names its files by gene and subfragment, so it kept only the last of such
     assays: Wilderlab's 12 assays in the SEA-MES data gave 7 sets of files, and now give 12. Before
     6 November the tool stopped with an error in this case.
7. **Values as written** (9 November 2026). Upstream reads each sheet with `comment='#'`, so a `#`
   anywhere in a cell cuts off the rest of the row, and with pandas' column types, so IDs written as
   text (`001`) become numbers (`1`). `faire2qiime_run.py` runs the upstream script with its three
   sheet reads sent to a reader that skips only the rows whose first cell starts with `#`, and keeps
   each cell's own type (`dtype=object`). Missing values are read as upstream reads them. No upstream
   file is changed, and the run stops if upstream no longer reads a sheet that way. On the test
   workbooks without such values, the outputs are byte for byte the same as upstream's. The copies
   made for assays converted one at a time (item 6) now keep text starting with `=` too.

## Upstream issues to report

- Generic FAIRe and FAIRe-ator layouts are not read (item 1 above). This matters most for
  Australian users, who are likely to make templates with FAIRe-ator.
- A `#` in any cell cuts off the rest of its row, as the sheets are read with `comment='#'` (to skip
  the two `#` rows above the field names): a station_id of `Sta1 #2` became `Sta1 ` and the sample's
  8 later fields were empty in the metadata table, without a warning. `header=2` in place of
  `comment` would avoid it; edna2obis already reads the sheets that way. Found 9 November; of the
  published FAIRe examples, only a targeted-assay workbook has `#` in its cells. The wrapper works
  around it (item 7).
- IDs written as text lose their leading zeros: a materialSampleID of `001` reaches the metadata
  table as `1`, as the sheets are read with pandas' column types. `dtype=str` would keep them. The
  wrapper works around it (item 7).
- Missing columns give a bare `KeyError` (item 2).
- The "Inconsistent assay names" check compares `unique()` with `dropna()`, so any row with an empty
  assay_name raises that error, with a message that does not point to the cause.
- The manifests always use absolute paths built from `--absolute_path_sequences`, which is required
  even when only the metadata is wanted.
- Output files are named by gene and subfragment, not assay_name, so assays on the same fragment
  overwrite each other (the verte_quadeloupe FAIRe example kept 4 of 22 rows).
- Empty file names become `nan` in the manifests.
- A tagged release and a pip or bioconda package would help (see below).

## Before deployment on Galaxy Australia

### Must do

1. **Talk to the upstream authors (NOAA 'Omics, AOML).** Tell them about the wrapper, offer the
   layout fix in `normalise_faire.py` as a pull request, and ask for a tagged release. The tool
   version is currently the commit date (`2026.07.23`).
2. **Test with an Australian workbook made by FAIRe-ator**, for example a filled-in MiFish or COI
   template. The test data here comes from the NOAA GOMECC-4 example, restructured to mimic the
   FAIRe-ator layout.
3. **Check the output in QIIME 2.** Load a metadata file with `qiime metadata tabulate`, and
   import a few samples with a manifest, to confirm QIIME 2 accepts both. QIIME 2 accepts
   `sample_name` as the ID column header, but this has not been checked here.
4. **Fill in `.shed.yml`.** Set `owner`, and add the maintainers to the
   `<creator>` block in `faire2qiime.xml`.
5. **Publish to the ToolShed** (Test ToolShed first), then **ask Galaxy Australia to install it**.

### Should do

6. **Decide how it fits with QIIME 2 in Galaxy.** If Galaxy Australia offers the QIIME 2 tools
   (q2galaxy), the useful output in Galaxy is the metadata file. The reads are imported from a
   paired collection whose element identifiers must match `sample_name`. A short workflow, or a
   page in the eDNA lab, showing *FAIRe workbook → FAIRe2QIIME metadata → QIIME 2 import* would
   help users. A later version of the wrapper could also write a two-column table for Galaxy's
   *Relabel identifiers* tool, to rename a fastq collection to match `sample_name`.
7. **Decide where the code lives long term.** As for FAIRe2ENA, the IUC expects a conda package;
   that needs a tagged upstream release or a consolidated FAIRe package.

## Test data

- `test-data/faire_two_assays.xlsx`: a cut-down copy of the GOMECC-4 generic FAIRe example in
  [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) (MIT), with four samples and their
  eight runs across two assays (16S and 18S). projectMetadata uses `assay1` and `assay2` columns.
  The same file is used by the FAIRe2ENA tests.
- `test-data/faire_single_assay.xlsx`: the same samples, 16S only, with the assay details moved
  into `project_level`, as FAIRe-ator writes a single-assay template.
- `test-data/faire_same_gene.xlsx`: `faire_two_assays.xlsx` with the 18S assay given the 16S
  assay's target_gene and target_subfragment, so the two would get the same file names.
- `test-data/faire_text_values.xlsx`: `faire_two_assays.xlsx` with `=see notes` in serial_number
  and `Sta1 #2` in station_id for `GOMECC4_27N_Sta1_DCM_A`, and materialSampleID `001` to `004`
  as text. Written by `dev/normalise_faire_differential/make_testdata.py`.
- `test-data/faire_same_gene_text_values.xlsx`: `faire_same_gene.xlsx` with `=see notes` in
  serial_number for `GOMECC4_27N_Sta1_DCM_A` (assays converted one at a time). Written by the same
  script.

The GOMECC-4 data reuse some `lib_id` values across the two assays. That is a feature of the
example data, and it shows up in the manifests as 16S-style IDs in an 18S run.

## Running the tests

```bash
pip install planemo
planemo lint faire2qiime/
planemo test faire2qiime/
```

## planemo test results

Run on 3 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (python 3.12, pandas 2.2.3, openpyxl 3.1.5). All tests passed, and all 5
again on 6 November with assays of the same gene converted one at a time, and all 7 on 9 November
after `normalise_faire.py` began copying values as they are and the wrapper began reading the
workbook for FAIRe2QIIME (item 7; tests 6 and 7).

| Test | Checks | Result |
|---|---|---|
| 1 | FAIRe layout, two assays: 2 metadata files and 3 manifests with the expected names, rows and paths | passed |
| 2 | Two assays of the same gene and subfragment: each converted on its own, 2 metadata files and 3 manifests named by assay_name, with a note in the log | passed |
| 3 | FAIRe-ator single-assay layout, metadata only: 1 metadata file, no manifests | passed |
| 4 | Suffix option adds `samp_name_unique` | passed |
| 5 | Sample ID column that does not exist: stops with a clear message | passed |
| 6 | Text values reach both metadata tables as written: `=see notes`, `Sta1 #2` (upstream alone cuts the row off at the `#`) and materialSampleID `001` (upstream alone writes `1`) | passed |
| 7 | Assays converted one at a time: `=see notes` reaches both metadata tables | passed |
