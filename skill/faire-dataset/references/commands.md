# faire_session.py commands

Run each as `python scripts/faire_session.py COMMAND ...`. Every command takes `--work FOLDER`
before the command name to use another session folder (the default is `faire_work` in the current
folder). `COMMAND --help` lists the options.

The script prints `STOPPED:` and the reason when something needs fixing, and exits with code 2.

## Setting up

| Command | What it does |
|---|---|
| `setup [--install]` | Checks Python has pandas, openpyxl, pypdf, pydantic and numpy; installs what is missing with `--install`. |
| `start --assay_type metabarcoding --sample_types Water --assays MiFish_12S,Fish16S --project_id Smith2025_Rivers --country Australia --utc_offset +08:00 [--date_order dmy]` | Records the study's settings. Run again with any option to change it. Assay names and the project ID take letters, digits, `_` and `-` only. |
| `status` | What has been done, and the next step. |

## Files and the sample table

| Command | What it does |
|---|---|
| `identify FILE ...` | Says what each file is (sample table, OTU or ASV table, taxonomy, library table, FASTA, methods text, data dictionary ...) and where it goes. Each Excel sheet is reported on its own. |
| `map TABLE [--sheet NAME] [--header_row N] [--dictionary FILE] [--earlier_review SHEET]` | Proposes a FAIRe term for each column of the sample table. Writes the review sheet. `--dictionary` takes a table of column descriptions or a README. `--earlier_review` carries decisions over from an earlier session's review sheet. |
| `map --again` | Maps the session's table again (after corrections), carrying over the decisions made so far. |
| `table set COLUMN --value V --where 'COLUMN=VALUE' [--nth N]` | Changes cells in a copy of the table. `--where` takes `COLUMN=VALUE` (exact) or `COLUMN~PATTERN` (a regular expression, case ignored); `--nth 2` changes only the second matching row. |
| `table add-column NAME [--value V]` | Adds a column, empty or with V in every row. |
| `table drop-column NAME` | Leaves a column out of the copy. |
| `table add-row --cells 'COLUMN=VALUE' ...` | Adds a row, such as a blank that is in the OTU table but not the sample sheet. |
| `table rename-column NAME --value NEW` | Renames a column. |
| `table set COLUMN --template '{Assay}{machine}' --all` | Fills cells from other cells of the same row (also with `add-column`). `--all` changes every row. |
| `table ... --file RESULTS.csv` | Corrects a copy of another table, such as qPCR results, in place of the sample table. `build` then uses the corrected copy when given the original's path. |
| `new-table OTU_TABLE [--split REGEX] [--join SITES --on 'HERE=THERE'] [--columns ...] [--exclude ...]` | For a study with no sample table: starts one with a row for each sample column of the OTU table. `--split` breaks the names into columns with a regular expression of named groups, such as `'(?P<Code>[A-Z]+[0-9]*)-(?P<Replicate>[0-9]+)'`; `--join` adds the columns of a site table. Then add what the researcher knows with `table`, and run `map` with no table. |
| `items [--all]` | The columns still to decide: values, candidate terms with their meanings, the mapper's reasoning, and the question for commonly confused terms. Then the additional checks. |
| `decide COLUMN accept` | Accepts the proposed term. |
| `decide COLUMN change TERM [--by-model]` | Uses another FAIRe term (or a MIxS or Darwin Core term as listed, such as `phosphate (MIxS term)`). `--by-model` records that the researcher agreed with a term you suggested. |
| `decide COLUMN reject` | Keeps the column under its own name, as a user-defined field. |
| `load-review columns FILE [--force]` | Takes back a review sheet the researcher filled in themselves. Stops if its columns do not match the table's. |

Give each `table` change a `--reason`; corrections are logged in `faire_work/table/corrections.tsv`
and listed in the handover.

## Methods and primers

| Command | What it does |
|---|---|
| `methods FILE ... [--whole_text] [--again]` | Reads methods text or PDF for values for the whole study (filtration, extraction, PCR, sequencing, bioinformatics), each with its sentence, and looks for primer pairs. `--whole_text` reads text with no Methods heading as a whole. |
| `method-items [--all]` | The method values still to decide, with row numbers, and the primer candidates. |
| `method-decide accept --row N` | Accepts a value. |
| `method-decide change "VALUE" --row N` | Records the right value. |
| `method-decide reject --row N` | Leaves a value out (it does not apply, or belongs to other work). |
| `method-decide accept --all-reliable [--except 9,14]` | Accepts every undecided value found reliably, after the researcher has read the list. |
| `method-decide accept --term TERM [--assay NAME]` | The same by term, when the term has one value. |
| `primers-use PAIR_ID --assay NAME [--with-target]` | Records the primer names, sequences, references and target gene of a pair from the candidates for one assay. `--with-target` also takes targetTaxonomicAssay from the reference table (ask first). |
| `primers-lookup NAME ... [--gene 12S]` | Finds pairs by primer or assay name or citation; then `primers-use PAIR_ID --assay NAME --lookup-file faire_work/methods/primer_lookup.tsv`. |
| `load-review methods FILE` | Takes back a method details review sheet the researcher filled in themselves. |

## Values the researcher gives

| Command | What it does |
|---|---|
| `set TERM VALUE [--assay NAME] [--source TEXT]` | Records a value for the whole study, or for one assay. Checks that the term exists and the value is allowed (`--force` keeps a value that is not). Says when the term is a commonly confused one, and when the value differs from what the methods give (the method details found, amplicon sizes in bp, and primer and probe sequences written in the methods). Project terms go to projectMetadata; sample terms are written for every sample unless a column of the table gives them. |
| `unset TERM [--assay NAME]` | Removes a value recorded with set. |
| `gaps [--recommended]` | Mandatory terms still without a value. With `--recommended`, also the highly recommended terms still empty that can apply to the study, by section (no qPCR probe terms for metabarcoding, no precipitation terms when the samples were filtered). |

## Building and checking

`build` writes the workbook from the reviewed sample table, the method values and the values given.
Tables are given as a path followed by `key=value` options:

```
build --otu PATH [assay=NAME] [run=RUN_ID] [stage=final|raw] [sequences=FASTA] [taxa=TAXONOMY]
                 [taxa_sheet=SHEET] [layout=detect|columns|rows|long] [sheet=SHEET]
                 [curated=COLUMN] [lineage=COLUMN] [assay_column=COLUMN]
      --library PATH [assay=NAME[,NAME]] [filter=TEXT] [run=RUN_ID] [sheet=SHEET]
      --amp PATH [assay_column=COLUMN] [sheet=SHEET]
      [--include_review] [--drop_unmapped] [--req_lev M,HR,R,O]
```

- `--otu`: an OTU or ASV table (reads per sequence or taxon and sample), one per assay and run.
  - `assay`: needed when the study has several assays.
  - `run`: its sequencing run ID (seq_run_id), when the table has no run column.
  - `stage`: `final` (curated, the default: otuFinal and taxaFinal) or `raw` (every ASV).
  - `sequences`: a FASTA file of its sequences, when the table names them but does not hold them
    (an LCA output, for example).
  - `taxa`: a separate taxonomy table, keyed by sequence ID or sequence.
  - `layout`: overrides the detection of samples as columns, rows or long form.
  - `curated`: the column of an ASV table that holds each ASV's curated name; the table then gives
    raw and final tables.
  - `lineage`: which lineage column to read when there are several (PR2 tax, Silva 138.1 tax).
  - `assay_column`: for one table that holds several assays (such as Wilderlab's target column).
- `--library`: a run report from ENA or the SRA, an SRA submission sheet, a lab's run sheet, a list
  of fastq file names, or md5sum output. It gives lib_id, file names, checksums and accessions.
  `filter` keeps only libraries whose name holds the text (one file list shared by two assays);
  `assay` can name two assays when one library holds both amplicons.
- `--amp`: qPCR or ddPCR results for a targeted assay, one row per reaction, with sample, assay and
  Cq or copies.
- `--include_review`: a draft that also applies matches still undecided (mandatory and commonly
  confused terms still wait for a decision). Use only when the researcher asks for a draft.
- `--drop_unmapped`: leaves out columns kept under their own names.

| Command | What it does |
|---|---|
| `check [--show N]` | Runs FAIRe-fier on the workbook and lists the errors and warnings, grouped. The full list is in `faire_work/check/`. |
| `summary` | Writes `faire_work/handover/` (workbook, review sheets, values, logs, FAIRe-fier results, converted files and a README of where every value came from) and a zip of it. |

## Converting

`convert TARGET [options]` converts the checked workbook into `faire_work/convert/TARGET/`. It stops
if the workbook has not been checked, or if FAIRe-fier found errors (add `--anyway` for a draft). It
prints the files written, the converter's messages (a message repeated for many samples is shown
once, with a count) and what to do with the files. Uploading stays with the researcher.

| Target | Writes | Options |
|---|---|---|
| `gbif` | A Darwin Core archive (`dwca.zip`: occurrences with the DNA derived data extension and EML), the tables on their own, and `report.md` (FAIRe to Darwin Core). Targeted assays give presence and absence records; metabarcoding gives presence records. Controls are left out. | `--publish_to gbif\|obis\|both`, `--licence CC0-1.0\|CC-BY-4.0\|CC-BY-NC-4.0`, `--given_name`, `--surname`, `--organisation`, `--email`, `--orcid`, `--title`, `--abstract`, `--keywords`, `--assays A,B`, `--no_absences`, `--taxa TABLE` (name, then scientificName, scientificNameID, taxonRank, kingdom ... genus), `--country_code AU` |
| `ncbi` | `biosample.tsv`, and for metabarcoding `sra.tsv` (FAIRe2NCBI). | `--organism "freshwater metagenome"`, `--bioproject PRJNA...`, `--mandatory_fill "not collected"` (or not provided, not applicable, missing, missing: control sample; default: stop and list the empty fields), `--duplicates_column COLUMN`, `--instrument_model` |
| `ena` | `samples.xml` and `submission.xml` (FAIRe2ENA). Experiments and runs need the receipt, so they run later in the Shiny app or Galaxy. | `--center_name` (required), `--taxon_id` (408172 marine, 449393 freshwater, 410658 soil, 655179 air metagenome) |
| `qiime` | QIIME 2 sample metadata and manifests, one set per assay (FAIRe2QIIME). | `--sample_name_column lib_id`, `--sequences_folder PATH` |

FAIRe2MDT (GBIF's Metabarcoding Data Toolkit) and edna2obis (OBIS) are not bundled: they need R or
the WoRMS and GBIF web services. They run in the Shiny app and Galaxy.

## The session folder

```
faire_work/
  session.json                 settings and where things are
  session_log.tsv              every step and decision, with the time
  identify/                    what each file is
  table/                       the corrected copy of the sample table, and the corrections
  map/out/                     the mapper's outputs (review sheet, crosswalk, report, checks)
  map/review_sheet_reviewed.xlsx   the review sheet with the decisions made
  map/decisions.tsv            each column decision, and who made it
  methods/                     method details (proposals and the reviewed sheet) and primer candidates
  values.tsv                   values the researcher gave or confirmed, with their source
  build/                       the workbook and apply mapping's log
  check/                       FAIRe-fier's outputs
  convert/                     the converted files, one folder for each target
  handover/ and *_handover.zip what to give the researcher
```
