# FAIRe2NCBI Galaxy wrappers

Two Galaxy tools that turn a FAIRe metadata workbook into the tables the NCBI Submission Portal
needs:

| Tool | Galaxy ID | Input | Output |
|---|---|---|---|
| FAIRe2NCBI: BioSample | `faire2ncbi_biosample` | FAIRe workbook (.xlsx) | BioSample table (MIMARKS survey, water 6.0), config, log |
| FAIRe2NCBI: SRA | `faire2ncbi_sra` | FAIRe workbook, optional BioSample accession table | SRA metadata table, config, log |

Upstream: [aomlomics/FAIRe2NCBI](https://github.com/aomlomics/FAIRe2NCBI) at commit
`ef62f3da0281596d926b1aaa6c7c6c4c728d9d90` (23 Jul 2026, the latest on `main` as of 3 Nov 2026).
CC0 licence.

## Status

- `planemo lint`: passes with no warnings.
- `planemo shed_lint`: passes except for the placeholder owner in `.shed.yml`.
- `planemo test`: all tests pass in Galaxy 25.0 (summary at the end of this file).
- Tested with FAIRe-ator layout workbooks (two assays, and one assay in `project_level`) and a
  FAIRe-NOAA layout workbook.
- Not yet tried in the NCBI Submission Portal.

## Files

| File | Purpose |
|---|---|
| `faire2ncbi_biosample.xml`, `faire2ncbi_sra.xml` | Galaxy tool definitions |
| `macros.xml` | Shared version, requirements, organism choice, outputs, help and citation |
| `scripts/FAIRe2NCBI.py`, `scripts/FAIRe2BioSample.py`, `scripts/FAIRe2SRA.py`, `scripts/paths.py` | Upstream scripts, copied unchanged |
| `docs/NCBI_BioSample_Metadata_Template.tsv`, `docs/NCBI_SRA_Metadata_Template.xlsx`, `docs/mixs.yaml` | Upstream templates and MIxS units, copied unchanged |
| `faire2ncbi_galaxy.py` | Galaxy driver that prepares the workbook and runs the upstream scripts (see below) |
| `normalise_faire.py` | Relabels FAIRe-ator assay columns by assay name; the same file as in `faire2qiime/` |
| `LICENSE.upstream` | Upstream CC0 licence |
| `test-data/` | Test workbooks and accession tables (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

`scripts/` and `docs/` keep the upstream layout, because `paths.py` finds the templates relative to
the scripts. Not included: `update_FAIRe_associatedSequences.py` and
`find_empty_corrupted_files.py` (they work on local fastq folders or update the workbook after
submission), the config templates (not used when a config is given) and `scripts/__init__.py`
(it imports a module that does not exist).

## What the wrapper adds

FAIRe2NCBI asks its questions with `input()`. In the test runs it asked 12 to 18 in BioSample mode
and 4 or 5 in SRA mode. A YAML config can answer them, but many depend on the data (one per numeric
field without a `_unit` field, per empty mandatory field, per assay). The driver imports the upstream modules and runs `FAIRe2NCBI.py`'s
`main()` with stdin closed. It answers each question from the form as it is asked, records the
answer, and writes all answers to the **config** output, which the upstream script accepts with
`--config_file`.

1. **Unanswered questions fail fast.** At end of input upstream raises `EOFError` with a
   traceback. The driver turns this into one plain error that names the question. If upstream
   rejects an answer and asks again, the driver stops after 20 repeats; upstream would loop for
   ever (see issues below).
2. **Works with FAIRe-ator workbooks.** SRA mode reads platform, instrument, target gene and
   primers from projectMetadata columns named by assay. `normalise_faire.py` relabels `assay1`,
   `assay2` ... (or copies `project_level` for a single assay) first. NOAA-layout workbooks pass
   through. BioSample mode does not need this, but the same copy is used.
3. **Collection dates.** NCBI wants times in UTC. Upstream passes `2021-09-14T11:00-04:00`
   through unchanged and writes Excel date cells as `2021-09-14 11:00:00`. The driver converts
   offsets to UTC (`2021-09-14T15:00Z`) and Excel cells to ISO dates, and warns about dates NCBI
   may not read (such as `7/6/19` in the NOAA example). Users can turn conversion off.
4. **Organism.** FAIRe has no `organism` term, so `*organism` is empty for every FAIRe-ator
   workbook, and upstream would fill it with "not collected", which NCBI rejects. The form offers
   common metagenome names; values already in the workbook are kept.
5. **Empty mandatory fields.** The driver lists every empty mandatory field and sample in one
   message, or fills them with the INSDC term the user picks. Upstream asks only about columns
   that are empty for every sample, and fills other gaps with "not collected" without asking.
6. **Units.** Upstream skips units for a whole column if any value is a missing-value term with a
   reason, such as `not applicable: control sample`. In the GOMECC example this drops the units
   from all 19 numeric fields. The driver widens upstream's set of missing-value terms at run time
   (no file is changed) so these fields get their `_unit` or MIxS units.
7. **Replicates.** NCBI will not register samples whose attributes are identical apart from name,
   title and description. Upstream asks for a field to add; the tool takes it from the form, or
   stops and lists the samples and the fields that would tell them apart.
8. **New samples and runs only.** BioSample mode keeps samples with no `associatedSequences` on any
   run. Upstream offers this filter only when BioProjects are assigned by a grouping field, so the
   driver applies it itself. SRA mode keeps runs whose own `associatedSequences` cell is empty.
   A cell holding `NA` or `N/A` counts as filled, as upstream reads it.
9. **Run selection.** The tool filters experimentRunMetadata rows by assay_name, seq_run_id or
   lib_id. Upstream selects lib_id values and then keeps every row with those lib_ids, so rows from
   other assays that reuse a lib_id come back in.
10. **Instruments.** FAIRe writes instruments as `Illumina MiSeq [OBI_0002003]`, which never
    matches NCBI's list. The driver removes the code, or sets the instrument and platform chosen on
    the form for all runs. The form lists NCBI's values from the SRA template.
11. **Linking runs to BioSamples.** Upstream's SRA table has no link to BioSamples registered in
    the same submission. The tool adds a `sample_name` column (and drops the empty
    `biosample_accession` column, as the NOAA 'Omics NCBI instructions advise), or fills
    `biosample_accession` from an accession table.
12. **Output checks.** The tool stops if a library_ID or file name is repeated, a library has no
    file, or (when linking by accession) a library has no accession. It also stops if upstream
    returns without writing its output, which upstream does after printing an error.
13. **Tidy log.** Colour codes are removed. The config lists the changes made to the workbook copy,
    so a local rerun can repeat them.
14. **Whole numbers and coordinates.** Upstream reads the workbook with pandas' column types. A
    column of whole numbers with an empty cell becomes decimal (14 is written as 14.0), and with
    units on, a column of whole numbers only (samp_store_temp, all -80) stops the run with a
    TypeError. Upstream also rounds lat_lon to 3 decimal places (about 100 m). While it runs, the
    driver replaces upstream's sheet reader with one that keeps each cell's own type, and its
    lat_lon formatter with one that keeps the decimal places of the workbook (no file is changed).
    Found in the trial on CSIRO's SEA-MES data (dev/faire_mapper_seames).
15. **Libraries that hold several assays.** When amplicons are pooled before indexing, one set of
    fastq files holds several assays, and experimentRunMetadata has a row for each assay with the
    same sample and files. Upstream writes an SRA row for each, which NCBI rejects as repeated
    files. The driver joins them into one row: the title names every assay
    (`M159: Fish16S and COILeray metabarcoding of ...`) and the design description gives each
    assay's own (`2 assays in one library. Fish16S: ...; COILeray: ...`). Rows that share a lib_id
    but not their files are left for the output checks, which stop with advice. Found in the trial
    on the SEA-MES 16S and COI data.
16. **One lib_id per amplicon.** FAIRe defines a library as "an amplicon of a sample with unique
    MIDs", so the FAIRe mapper writes lib_id as the library name, assay_name and seq_run_id
    (`M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12`), and a library that holds two amplicons has two
    lib_ids. library_ID is the library's own name, so the driver takes the assay and run off again
    (`M097_16SFish_LerayCOI`), keeping the run, then the whole lib_id, where names would repeat (a
    library sequenced in two runs). Rows joined under one lib_id for several assays (item 15) are
    still accepted, with a note that FAIRe expects one lib_id per amplicon.
17. **Text values.** `normalise_faire.py` and the driver used to read the workbook with pandas'
    default missing values, so text such as `NA` or `N/A` became an empty cell, and saved it with
    openpyxl, which turns text starting with `=` into a formula with no value. Both now keep cell
    values as they are. The driver then reads each sheet as upstream does: text such as `NA` is
    empty in sampleMetadata and projectMetadata (so the form's fill for empty mandatory fields
    applies to it, and the log counts these cells), and a value in experimentRunMetadata, where
    upstream reads `NA` or `N/A` in associatedSequences as filled. Before, runs marked `NA` were
    offered as new. Found with the differential check in `dev/normalise_faire_differential`.

Python warnings: Galaxy sets `PYTHONWARNINGS=ignore`. FAIRe2NCBI reports everything with
`print()`, so nothing is lost.

## Decisions

- **Two tools.** BioSample and SRA are separate steps in the NCBI portal and have different inputs.
- **Scope.** BioSample and SRA metadata tables only. Fastq checking (`--filter-fastq`), splitting by
  BioProject with fastq symlinks (`--split_by_BioProject`, `--fastq_folder`) and
  `update_FAIRe_associatedSequences.py` need local folders and are left for later. With several
  BioProjects in an accession table, the tool writes one combined file.
- **One BioProject for all samples.** Upstream can also assign BioProjects by a grouping field
  (for example expedition_id); this is not on the form yet.
- **BioProject accessions** accepted as `PRJNA`, `PRJEB` or `PRJDB` followed by digits, or empty.
- **Empty mandatory fields** stop the tool by default. Filling them silently would hide gaps that
  NCBI or reviewers may question.
- **Default organism** is *marine metagenome*, the same default as the FAIRe2ENA tool.
- **library_strategy, library_source, library_selection** stay at upstream's defaults (AMPLICON,
  METAGENOMIC, PCR), which suit eDNA metabarcoding.
- **Instrument list** is the NCBI template's list, limited to the instruments upstream accepts for
  each platform (80 values).
- **SRA filter by row.** SRA mode keeps runs with an empty `associatedSequences` cell. Upstream
  keeps whole samples, so a new 18S run of a sample whose 16S run is already in SRA would be
  missed.
- **Output format** `tsv`, so files download with a `.tsv` extension for the NCBI portal.
- **`normalise_faire.py` fix.** It stopped on a multi-assay NOAA-layout workbook (`A | B` in
  `project_level` with columns already named A and B). It now passes these through. The fix is
  also in `faire2qiime/normalise_faire.py`, so the two copies stay identical.

## Upstream issues to report

Evidence for each is in the wrapper's test data or the upstream code at the pinned commit.

- **Prompts at end of input** raise `EOFError` with a traceback. A `--no-input` or batch mode
  that fails with the question text would help pipelines.
- **Endless loops on a rejected config answer.** For example
  `lib_id_selected_values_input_assay_name: ssu16sv4v5-emp` (a name, not a number) printed
  "is not a valid number" 2.5 million times in 20 seconds (a 349 MB log), and
  `platform_value_input: FOO` printed "is not a valid platform" 787,066 times in 10 seconds.
- **FAIRe-ator layout not read in SRA mode**: no platform is found for `assay1`, `assay2`
  columns, so it asks "Enter platform value" for each assay, and the target gene and primers in
  design_description would be "NA" (item 2 above).
- **Empty terms written into design_description**: an empty `target_subfragment` or
  `nucl_acid_amp`, or a FAIRe missing value such as `not applicable`, gives "gene NA region" and
  "using protocol at NA" (`FAIRe2SRA.py` line 2308). Since version 2026.07.23+galaxy3 the wrapper
  leaves those phrases out.
- **associatedSequences filter in BioSample mode** is only offered on the grouping-field path
  (`FAIRe2BioSample.py` line 2741).
- **Units dropped** when a column holds `not applicable: control sample` or similar (item 6).
- **IDs written as text lose their leading zeros** when upstream reads the workbook itself (a
  materialSampleID of `001` becomes 1). The driver's typed reader (item 14) keeps them.
- **Offset datetimes and Excel date cells** passed to `*collection_date` unchanged (item 3).
- **FAIRe instrument values** (`... [OBI_xxxx]`) never match NCBI's list (item 10).
- **lib_id selection by assay or run** keeps rows from other assays that share a lib_id: choosing
  one assay of the GOMECC example gave 8 rows across 2 assays.
- **No link from SRA rows to new BioSamples** (no `sample_name` column) unless an accession table
  is given.
- **Rows without a samp_name** become a BioSample named "not collected".
- **"leave blank to skip"** for an empty mandatory column still fills it with "not collected"
  (lines 2785 to 2787).
- **Config not saved** when the output path has no folder (`os.makedirs('')` fails:
  "Could not save configuration file bs_config.yaml").
- **Errors return exit code 0** (for example "Error: Could not read sampleMetadata" then `return`).
- **`scripts/__init__.py`** imports `.cli`, which does not exist, so `import scripts` fails.
- **Platform lists** in `FAIRe2SRA.py` differ from NCBI's template: FASTASeq 300 is under GENAPSYS
  (NCBI: GENEMIND) and Onso also under ELEMENT (NCBI: PACBIO_SMRT only).
- **design_description** reads assay terms only from assay columns, so a value given once in
  `project_level` (such as `nucl_acid_amp` in the NOAA example) becomes "NA".
- **No organism term in FAIRe**: worth agreeing with the FAIRe authors how `*organism` should be
  supplied.
- A tagged release and a pip or bioconda package would help, as for the other FAIRe tools.

## Before deployment on Galaxy Australia

### Must do

1. **Talk to the upstream authors (NOAA 'Omics, AOML).** Tell them about the wrapper and the issues
   above, offer the `normalise_faire.py` layout fix, and ask for a tagged release. The tool
   version is currently the commit date (`2026.07.23`).
2. **Trial a submission in the NCBI Submission Portal** with an Australian FAIRe-ator workbook:
   upload the BioSample table, then the SRA table linked by sample_name, and check that NCBI
   accepts the attribute values, units, `missing: control sample` style terms and the
   `not applicable: control sample` values from the example data. NCBI has a test mode; do not
   finish a real submission with test data.
3. **Check the organism names** against NCBI Taxonomy. Confirmed on NCBI Taxonomy on 5 November
   2026: *seawater metagenome* (1561972), *soil metagenome* (410658) and *metagenome* (256318). The
   others (*marine metagenome* 408172, *freshwater metagenome* 449393, *aquatic metagenome*
   1169740, *estuary metagenome* 1649191, *marine sediment metagenome* 412755, *freshwater sediment
   metagenome* 556182) match NCBI pages in web searches, but NCBI's browser check stopped the pages
   opening from here; open them in a browser to finish.
4. **Fill in `.shed.yml`.** Set `owner`, and add the maintainers to
   the `<creator>` block in `macros.xml`.
5. **Publish to the ToolShed** (Test ToolShed first), then **ask Galaxy Australia to install it**
   in the eDNA lab, next to FAIRe2ENA.

### Should do

6. **Add BioProject assignment by a grouping field** (upstream's expedition_id workflow), if
   Australian users need several BioProjects in one workbook.
7. **Fastq steps.** If the reads are in the Galaxy history, a later version could check for empty
   or corrupt files and compare file names with experimentRunMetadata.
8. **Write a short guide** in the eDNA lab: *FAIRe workbook → FAIRe2NCBI: BioSample →
   FAIRe2NCBI: SRA → NCBI Submission Portal*, including how to upload fastq files to NCBI.
9. **Decide where the code lives long term.** As for the other wrappers, the IUC expects a conda
   package, which needs a tagged upstream release or a consolidated FAIRe package.

## Test data

- `test-data/faire_ncbi_two_assays.xlsx`: the FAIRe2QIIME test workbook (a cut-down GOMECC-4
  generic FAIRe example from [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis), MIT;
  four samples, eight runs, two assays, `assay1` and `assay2` columns) with these edits:
  - `GOMECC4_27N_Sta1_DCM_B` has the same eventDate text, `samp_size` and `samp_vol_we_dna_ext` as
    replicate A, so the two are identical apart from their names (tests replicate handling);
  - `GOMECC4_BROWNSVILLE_Sta63_DCM_A` has eventDate as an Excel date cell (2021-10-02);
  - the negative control has an empty `geo_loc_name` (tests mandatory fields);
  - `associatedSequences` is empty except for replicate B's two runs (tests new samples and runs).
- `test-data/faire_ncbi_shared_library.xlsx`: `faire_ncbi_two_assays.xlsx` with each 18S run given
  the lib_id and file names of the same sample's 16S run, so each library holds both assays (tests
  the joining of shared libraries).
- `test-data/faire_ncbi_amplicon_libraries.xlsx`: the same workbook with one lib_id per amplicon
  (library name, assay_name and seq_run_id, as the FAIRe mapper writes it), and the 18S rows given
  the run of the 16S rows whose files they share (tests joining by files and library_ID as the
  library's own name).
- `test-data/faire_ncbi_single_assay.xlsx`: the FAIRe2QIIME single-assay workbook, unchanged (16S
  only, assay details in `project_level`, one eventDate as an Excel date-time cell).
- `test-data/faire_noaa_layout.xlsx`: FAIRe-NOAA layout, built from the
  `FAIRe_NOAA_example_dataset_small` TSVs in edna2obis (NOAA SEFSC GU19-01 cruise, two 12S assays).
  Five samples (three seawater samples, two negative controls) and their ten runs. The
  `# ` prefix and byte order mark on the first two rows were removed, the extra empty cell on one
  projectMetadata row was dropped, and numbers were stored as numbers. No organism column.
- `test-data/faire_noaa_text_values.xlsx`: `faire_noaa_layout.xlsx` with `NA` and `N/A` in
  associatedSequences for both runs of `GU190707-CTD13-310`, `=see notes` in serial_number for
  `GU190706-CTD11-220`, `Bottle #3` in serial_number and `NA` in env_medium for
  `GU190707-CTD14-315`, and materialSampleID `001` to `005` as text (tests text values, item 17,
  and the typed reader of item 14). Written by `dev/normalise_faire_differential/make_testdata.py`.
- `test-data/biosample_accessions.tsv`: an NCBI-style accession table (`accession`, `sample_name`,
  `bioproject_accession`) for the four GOMECC-4 samples, with their public accessions.
- `test-data/accessions_odd_columns.tsv`: the same accessions under the headers `BioSample` and
  `Name`, which upstream cannot recognise (tests the unanswered-question error).

## Running the tests

```bash
pip install planemo
planemo lint faire2ncbi/
planemo test faire2ncbi/
```

## planemo test results

Run on 4 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (python 3.12, pandas 2.2.3, openpyxl 3.1.5, pyyaml 6.0.3), after the
workarounds for whole numbers and lat_lon (item 14 above), and again on 5 November after the
joining of shared libraries (item 15) and one lib_id per amplicon (item 16). All 17 tests passed,
and all 20 on 9 November with the text-values tests (item 17), then again with checks that a `#`
inside a cell and IDs such as `001` are kept.

| Tool | Test | Checks | Result |
|---|---|---|---|
| faire2ncbi_biosample | 0 | Whole numbers with MIxS units: samp_store_temp all -80 gets its unit, depths with an empty cell stay whole (49 meter), lat_lon keeps 7 decimal places | passed |
| faire2ncbi_biosample | 1 | FAIRe-ator layout, two assays: offset date to UTC, Excel date cell, units, BioProject, empty mandatory field filled, replicates told apart by replicate_number | passed |
| faire2ncbi_biosample | 2 | Empty mandatory field with the default setting: stops and names the field and sample | passed |
| faire2ncbi_biosample | 3 | Identical replicates and no field to tell them apart: stops, lists them and suggests fields | passed |
| faire2ncbi_biosample | 4 | New samples only; no extra fields; no titles | passed |
| faire2ncbi_biosample | 5 | FAIRe-NOAA layout: organism added, custom titles, one field left out, no MIxS units, date warning | passed |
| faire2ncbi_biosample | 6 | Single assay in project_level, defaults; warning for a time without a time zone | passed |
| faire2ncbi_biosample | 7 | Text values, new samples only: a sample whose runs have NA and N/A in associatedSequences is left out, `=see notes`, `Bottle #3` and materialSampleID `001` are kept, and NA in env_medium gets the form's fill value | passed |
| faire2ncbi_biosample | 8 | NA in a mandatory field with the default setting: stops and names the field and sample | passed |
| faire2ncbi_sra | 1 | One assay: 4 rows, NCBI header, sample_name link, instrument without OBI code, design_description | passed |
| faire2ncbi_sra | 2 | All runs, each library holding both assays: 4 rows, title and design description naming both | passed |
| faire2ncbi_sra | 3 | All runs with lib_id reused across assays with different files: stops with advice | passed |
| faire2ncbi_sra | 4 | FAIRe-NOAA layout, two assays, instrument chosen on the form: 10 rows | passed |
| faire2ncbi_sra | 5 | BioSample accessions from an accession table | passed |
| faire2ncbi_sra | 6 | Accession table with unexpected headers: unanswered question reported as a plain error | passed |
| faire2ncbi_sra | 7 | One sequencing run, runs not yet submitted only | passed |
| faire2ncbi_sra | 8 | Unknown assay name: stops and lists the assays | passed |
| faire2ncbi_sra | 9 | Single assay in project_level, defaults | passed |
| faire2ncbi_sra | 11 | Runs not yet submitted only: runs with NA and N/A in associatedSequences are left out (8 of 10 kept) | passed |
