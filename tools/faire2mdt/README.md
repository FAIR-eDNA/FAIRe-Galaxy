# FAIRe2MDT Galaxy wrapper

One Galaxy tool (`faire2mdt`) that converts FAIRe metabarcoding data for one assay and one
sequencing run into the Excel workbook taken by GBIF's
[Metabarcoding Data Toolkit](https://www.gbif.org/metabarcoding) (MDT).

| Input | Output |
|---|---|
| FAIRe metadata workbook (.xlsx), assay name, sequencing run ID, OTU table (otuFinal) and taxonomy table (taxaFinal) as Excel sheets, TSV or CSV | MDT workbook (sheets Study, Samples, Taxonomy, OTU_table), log |

Upstream: [FAIR-eDNA/FAIRe2MDT](https://github.com/FAIR-eDNA/FAIRe2MDT) at commit `13d1fcc`
(script version 1.1.0, 16 Jul 2025, the latest on `main` as of 3 Nov 2026). CC BY 4.0: the licence
file was added upstream on 11 November 2026 (`a1f83d0`, which changes nothing else) and is copied in
here as `LICENSE.upstream`.

## Status

- `planemo lint`: passes with no warnings.
- `planemo test`: all 6 tests pass in Galaxy 25.0 (summary at the end of this file).
- Run on the 11 assay and run combinations of the FAIRe example workbooks that have otuFinal and
  taxaFinal tables: all 11 converted (5 by hand). See `dev/faire2mdt/README.md`.
- Uploaded to MDT's test site on 3 November 2026 (IOT-eDNA, COILeray, Library_2021): MDT accepted
  the workbook and processed it (95 samples, 578 sequences, 74,767 reads, as in the OTU table). At
  the mapping step it took the Study values as defaults and mapped id, eventDate and the
  coordinates itself. It also took target_gene (COI, which is a GBIF term). The same run made by
  hand gave the same mapping page,
  apart from the coordinates (-10.541550000000001 and 105.70851999999999 by hand, -10.54155 and
  105.70852 from the wrapper). Not yet taken past the mapping step.
- NECR534 (12S-V5, Run1), after the target_gene change: on MDT's mapping page, target_gene was
  filled in as 12S ribosomal small subunit RNA (mitochondrial) and eventDate showed dates
  (2023-06-01). The workbook's own `NA` text values (verbatimEventDate, probeReporter and others)
  pass through as text. Processing gave the right totals (18 samples, 1,238,853 reads), but the
  Review page's bar chart did not match the data. That workbook's OTU table had 1,161 empty cells,
  and MDT had read each row without its empty cells, moving counts to the wrong samples (the
  chart matches the table exactly when each row's values are shifted left in this way). The
  wrapper now writes empty count cells as 0 (item 4). With that workbook, the Review page's class
  bar chart matched the data for all 18 samples. MDT's Metadata step (title, licence, contacts,
  coverage) was empty: from a workbook in this layout, MDT uses the Study sheet only as default
  field values (`workers/xlsxvalidationworker.js`). It fills the dataset metadata from
  projectMetadata only for its own FAIRe upload format (`workers/fairevalidationworker.js`). So
  with this tool's output, the metadata has to be typed into MDT. MDT then made a Darwin Core
  archive, and GBIF's data validator found that it can be indexed: 891 occurrences (one for each
  OTU table cell with reads), no issues in eml.xml or the DNA-derived data extension. Flags on the
  occurrences: target_gene invalid on all 891, although the archive holds
  SSU_rRNA_12S_mitochondrial, the term MDT takes from GBIF's own vocabulary (a question for GBIF);
  recorded date invalid on 54, all from sample FK1269, whose eventDate in the workbook is
  `missing: not collected`; and informational flags (country and continent derived from the
  coordinates, coordinates rounded, WGS84 assumed, no institution match, ASV taxon IDs not found).

## Files

| File | Purpose |
|---|---|
| `faire2mdt.xml` | Galaxy tool definition |
| `faire2mdt_galaxy.R` | Driver: reads the inputs, checks them, runs the upstream conversion code, checks the result |
| `FAIRe2MDT.R` | Upstream script, copied unchanged |
| `mdt_target_gene.tsv` | FAIRe target_gene values and the GBIF terms MDT stores for them (made by `dev/faire2mdt/make_target_gene_table.py`) |
| `test-data/` | Made-up test data (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `LICENSE.upstream` | FAIRe2MDT's CC BY 4.0 licence |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

## How the wrapper works

`FAIRe2MDT.R` has a section the user edits (working directory, assay name, sequencing run, input
file names), then the conversion code from the line `# Run the below code`. The driver replaces the
user section: it reads the Galaxy inputs into the same five tables (`Project`, `Samples`, `expRun`,
`otu`, `taxa`), checks them, and then runs the upstream code from that line to the end, unchanged.
The workbook it writes becomes the Galaxy output. A future upstream version can be dropped in as
long as it keeps that line and those table names.

## What the wrapper adds

1. **Exact matching of assay and run.** Upstream selects rows of experimentRunMetadata with
   `grepl`, so `COILeray` also takes `COILeray2`, `run1` also takes `run10`, and characters such as
   `+` or `(` change the match. The driver selects rows whose assay_name and seq_run_id equal the
   names given (ignoring case). If there are none, it uses names that differ only in punctuation or
   case (`12S_V5` for `12S-V5`) and says so in the log. The upstream filter is then given the chosen
   rows only, and its `grepl` is set to keep them all. The log also says when running the script by
   hand would have taken more rows.
2. **Dates and numbers as Excel shows them.** Upstream reads sampleMetadata, experimentRunMetadata
   and taxaFinal with `col_names = FALSE`, which makes every column text. Excel dates then come out
   as serial numbers (2024-03-05 becomes 45356, 09:25 becomes 0.392...), and numbers come out with
   17 significant digits (105.70852 becomes 105.70851999999999). The driver reads each cell with its
   type and writes dates as ISO 8601 (2024-03-05, 09:25:00, 2024-03-05T09:25:00) and numbers with up
   to 15 significant digits. The values are still written as text, as upstream does.
3. **Plain messages before the conversion starts**, for problems that would otherwise stop the
   script with an R error or give an empty sheet: missing sheets or columns, an assay or run not in
   the workbook (the message lists the assay and run pairs it has), an assay missing from the
   assay_name row of projectMetadata, a sample with more than one row for the same assay and run,
   and duplicate seq_id values in the OTU table.
4. **Empty OTU table cells written as 0**, with a note in the log. MDT reads each OTU table row
   without its empty cells, so counts after an empty cell move to the wrong samples, while the
   totals stay right (see Status). FAIRe otuFinal tables hold read counts, so an empty cell means
   no reads.
5. **Checks on the result**, written to the log as warnings: OTU table columns that are not
   samples of this assay and run, samples with no OTU table column, sequences in one of the OTU and
   taxonomy tables but not the other, and empty or text columns in the OTU table. Taxonomy rows
   whose sequence has no OTU table row are left out, with a note: FAIRe's taxaFinal lists every ASV
   of the final taxa, and otuFinal sums each taxon's reads under its most abundant ASV (as in the
   SEA-MES 16S data: 2,613 ASVs in taxaFinal, 235 rows in otuFinal), and MDT wants one taxonomy row
   for each OTU table row.
6. **More input forms.** OTU and taxonomy tables can be Excel sheets (of the metadata workbook or a
   separate file), TSV or CSV. A file with one sheet is read whatever the sheet is called. An OTU
   table whose top-left cell is empty (as R and many other programs write it) is read with its
   first column as seq_id.
7. **target_gene as a GBIF term.** MDT takes target_gene from the Study sheet only when it names a
   term of the GBIF target_gene vocabulary, by the term itself, its label or an alternative label
   (MDT backend, `util/targetGeneVocabulary.js`). That holds for 23 of FAIRe's 28 values, but not
   for five rRNA genes: 12S rRNA (SSU mitochondria), 16S rRNA (LSU mitochondria), 23S rRNA (LSU
   prokaryote), 18S rRNA (SSU eukaryote) and 28S rRNA (LSU eukaryote). For those MDT keeps the
   value, warns that it is not in the vocabulary, and the marker has to be chosen by hand. The
   driver writes the GBIF term for every FAIRe value (SSU_rRNA_12S_mitochondrial for 12S, and so on;
   ITS1 or ITS2 for ITS when target_subfragment says so) and notes the change in the log. It warns
   about values that are not FAIRe values (such as `other: ...`). The table comes from MDT's bundled
   copy of the vocabulary (captured 1 October 2026); the live vocabulary at api.gbif.org may have
   more alternative labels. In the FAIRe examples, 8 of the 11 runs needed this (all 12S and
   mitochondrial 16S).
8. **Control samples left out** (from the FAIRe authors' advice, 6 November 2026): GBIF does not
   want controls, so samples whose samp_category is negative control, positive control or PCR
   standard, or that have a neg_cont_type or pos_cont_type, are left out of the Samples and
   OTU_table sheets, with the sequences that only they have reads of (and those sequences'
   taxonomy rows). The log lists them. *Control samples: Keep them* includes them, and writes a
   control's `missing: not collected` as `not applicable: control sample`, FAIRe's term for a value a
   control does not have. A sample's `missing: not collected` (an eventDate, for example) is kept,
   as it is INSDC's term; whether GBIF wants it or an empty field is a question for GBIF.
9. **R packages from conda,** so the script's `install.packages()` step never runs.

## Decisions

- **One assay and run per job,** as upstream. For several, run the tool once for each (a Galaxy
  workflow can do this). Matching OTU and taxonomy files to assays and runs by name would add
  little for the usual one or two runs.
- **The upstream code is run, not rewritten,** so its conversion rules stay the authors'.
  Replacing `grepl` inside it is the one change to how it runs, and is listed above.
- **Warnings do not stop the tool.** MDT checks the workbook again on upload, and some warnings
  (for example blank samples with no reads) may be expected.

## Upstream issues to report

To the FAIRe2MDT authors (FAIR-eDNA):

1. ~~**No licence file.**~~ Done 11 November 2026: the authors added a CC BY 4.0 licence file
   (they had earlier given CC BY-SA 4.0), copied here as `LICENSE.upstream`. `FAIRe2MDT.R` is
   bundled unchanged, with its licence and credit to its authors. `faire2mdt_galaxy.R`, the Galaxy
   driver, runs it and replaces `grepl` inside it at run time; it is MIT, like the other wrappers.
2. **Assay and run matched as part of the text** (wrapper item 1). In the test workbook, assay
   `MiFish` with run `run1` gives 7 Samples rows in place of 3: S1 and S2 twice (also
   from MiFish-E), and S3 twice from run10.
3. **Excel dates and numbers changed** (wrapper item 2). Seen in the FAIRe examples: NECR534
   eventDate 2023-06-01 becomes 45078 and mod_date becomes 45416; IOT-eDNA decimalLongitude
   105.70852 becomes 105.70851999999999.
4. **Unclear errors.** An assay missing from projectMetadata stops with
   `Can't extract columns past the end`; an assay or run spelt differently in experimentRunMetadata
   (NECR534: 12S-V5 and 12S_V5) stops with ``Column `assay_name` doesn't exist``; an OTU table
   without a seq_id header (verte_guadeloupe) stops with ``Can't find column `seq_id` ``.
5. **The OTU_table sheet's first column has no header** (written with `rowNames = TRUE`). MDT
   accepted it.
6. **target_gene for five rRNA genes is not recognised by MDT** (wrapper item 7). The script could
   write the GBIF term.

To GBIF (target_gene vocabulary and MDT). Items 7 to 9, and the questions under "MDT's own FAIRe
import", were sent on 3 November 2026 to the GBIF helpdesk and the MDT developers:

7. **Add FAIRe's five rRNA names as alternative labels** in the GBIF target_gene vocabulary
   (12S rRNA (SSU mitochondria) for SSU_rRNA_12S_mitochondrial, and so on). One of FAIRe's rRNA
   names, 16S rRNA (SSU prokaryote), is already there. With all five, MDT and any other tool using
   the vocabulary would read FAIRe values directly, and wrapper item 7 would no longer be needed.
8. **MDT moves OTU counts to the wrong samples when a row has empty cells** (wrapper item 4).
   Nothing on the Process page shows it: sample, read and taxon totals are unchanged. Either read
   empty cells as 0 or stop with a message.
9. **GBIF's data validator flags MDT's target_gene as invalid.** MDT stores the term name from
   the GBIF target_gene vocabulary (SSU_rRNA_12S_mitochondrial), but the validator reported
   TARGET_GENE_INVALID for every record of the NECR534 archive.

The workbook issues found in the FAIRe examples are in `dev/faire2mdt/README.md`.

## MDT's own FAIRe import

The MDT backend ([gbif/metabarcoding-data-toolkit-backend](https://github.com/gbif/metabarcoding-data-toolkit-backend),
Apache 2.0, read at commit `91506ee`, 6 October 2026) has an upload format called *FAIRe format*:
projectMetadata, sampleMetadata, experimentRunMetadata, otuFinal and taxaFinal, as one workbook or
as separate files named with FAIRe prefixes (`converters/faire.js`). It takes one assay at a time,
takes default values and EML metadata from projectMetadata, and checks target_gene against the
GBIF vocabulary. If the MDT site in use has this, a FAIRe workbook may go to MDT without this tool.

From a first read of that code (not yet tried):

- It takes the assay from the otuFinal sheet or file name (the part after the first `_`), so an
  assay name containing `_` (such as `12S_V5`) would be cut short.
- It expects assay names as projectMetadata column headings (FAIRe-NOAA layout). FAIRe-ator
  workbooks (`assay1`, `assay2`) get a warning that the assay is not found in projectMetadata.
- With several runs of one assay, it seems to use the first otuFinal table for that assay.
- It meets the same target_gene gap (wrapper item 7), and reads cell values its own way, so dates
  need checking.

Uploading a FAIRe workbook straight to MDT (CPR_2015.xlsx has otuFinal and taxaFinal sheets) would
show whether the site has the FAIRe format, and what this tool still adds.

## Before deployment on Galaxy Australia

### Must do

1. ~~**Add the licence file upstream** and copy it here as `LICENSE.upstream`.~~ Done 11 November
   2026 (CC BY 4.0). The driver is MIT.
2. **Answer the GBIF questions from the MDT trial** (upstream items 8 and 9): the target_gene flag
   from the data validator, and whether MDT's own FAIRe upload makes this tool unnecessary. The
   trial itself is done: the NECR534 workbook went through MDT to an archive GBIF can index.
   openxlsx also writes references to drawing parts it leaves out of the file; MDT and pandas read
   such files, but openpyxl cannot open them in full (as with FAIRe-ator's templates), so check
   Excel too.
3. **Fill in `.shed.yml`** (owner) and add the wrapper maintainers to `<creator>`.

### Should do

1. Report the upstream issues above, and offer the exact matching and cell reading as changes
   upstream.
2. Try it on a real Australian dataset with its own OTU and taxonomy tables.
3. Check `mdt_target_gene.tsv` against the live GBIF vocabulary from time to time, and rebuild it
   when the FAIRe checklist or the vocabulary changes.
4. Consider a version that makes one MDT workbook for every assay and run in a workbook, taking
   collections of OTU and taxonomy tables matched by FAIRe file names
   (`otuFinal_<project>_<assay>_<run>`).

## Test data

Made up for the tests by `dev/faire2mdt/make_test_data.py` (all files under 10 KB):

- `mdt_workbook.xlsx`: a FAIRe workbook with two assays whose names overlap (MiFish, MiFish-E) and
  two runs whose names overlap (run1, run10), Excel date and time cells, a number stored as Excel
  stores it (105.70851999999999 in the sheet XML), a negative control (NC1) whose eventDate is
  `missing: not collected`, and OTU and taxonomy sheets for MiFish-E run1.
- `otuFinal_mdttest_MiFish_run1.xlsx` and `taxaFinal_mdttest_MiFish_run1.tsv`: OTU and taxonomy
  tables for MiFish run1.
- `otuFinal_mdttest_MiFish_run1.csv`: the same OTU table as CSV, with an extra column S9 that is
  not a sample of the run.
- `taxa_one_sheet.xlsx`: the taxonomy table in a workbook whose only sheet is called Sheet1.
- `taxaFinal_extra_asv.tsv`: the taxonomy table with a fourth ASV, a second Pagrus auratus ASV whose
  reads otuFinal sums under ASV_1, as in FAIRe's final tables.

The taxonomy rows (Pagrus auratus and others) are made up for the tests; they do not come from any
analysis.

| Test | Checks |
|---|---|
| 1 | MiFish, run1, OTU table in its own workbook, taxonomy as TSV: four sheets; only MiFish run1 libraries, without the negative control (log note); dates as 2024-03-05, 09:25:00 and 2026-11-03; 105.70852; target_gene written as SSU_rRNA_12S_mitochondrial; log notes the 4 rows a by-hand run would add and the target_gene change, no warnings |
| 2 | `MiFish_E`, `RUN1`, both tables as sheets of the metadata workbook: MiFish-E used (log note), Study takes the MiFish-E primer |
| 3 | OTU table as CSV with an empty cell, taxonomy workbook with one sheet called Sheet1: log notes the sheet used and the empty cell written as 0, and warns that S9 is not a sample of the run |
| 4 | taxaFinal with an ASV that has no otuFinal row: left out of the Taxonomy sheet, with a note, and no warning |
| 5 | Controls kept: the negative control's library is in, and its eventDate `missing: not collected` is written as `not applicable: control sample` (log note) |
| 6 | Assay not in the workbook: stops, listing the assay and run pairs the workbook has |

## Running the tests

```bash
pip install planemo
planemo lint faire2mdt/
planemo test faire2mdt/
```

## planemo test results

Run on 3 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (r-base 4.4.3, r-readxl 1.6.0, r-openxlsx 4.2.9, r-dplyr 1.2.1,
r-tibble 3.3.1). All 4 tests passed. On 6 November, with the taxonomy rows that have no OTU table
row left out, the controls left out, and a test for each, all 6 passed.
