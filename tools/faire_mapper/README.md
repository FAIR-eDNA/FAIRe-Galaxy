# FAIRe mapper Galaxy tools

Galaxy tools for the AI-assisted pipeline in the FAIRe concept note: they propose how the columns
of a lab's own sample sheet map to FAIRe terms, find primer sequences, and write a FAIRe workbook
from the reviewed mapping.

Developed by Oliver Berry (CSIRO), with Claude (Anthropic).

| Tool | Galaxy ID | Input | Outputs |
|---|---|---|---|
| FAIRe mapper: profile columns | `faire_mapper_profile` | CSV, TSV or Excel table | one row per column describing its values |
| FAIRe mapper: propose mapping | `faire_mapper_map` | the table, optional answers file | mapping report, SSSOM crosswalk, mandatory terms not covered, columns to review, additional checks to make, summary, review sheet |
| FAIRe mapper: find primers | `faire_primers_find` | methods text, or primer names and citations; optional own primer table | candidate primer pairs with sequences, references and sources |
| FAIRe mapper: build primer table | `faire_primers_build` | primer spreadsheets or TSVs | a primer table (added to the bundled one, or new), problems found |
| FAIRe mapper: apply mapping | `faire_mapper_apply` | the table, the reviewed crosswalk, optional values for the whole project, optional OTU and taxonomy tables, optional library tables | FAIRe workbook in the FAIRe-ator layout, with OTU and taxonomy sheets; log |

Every tool's help includes the same guide, **What inputs the FAIRe mapper can work with**
(`@HELP_INPUTS@` in `macros.xml`; also in `docs/faire_mapper_inputs.md` at the top of the repository,
for the Galaxy eDNA Lab pages): the steps and the Galaxy tool for each, the files people can give and
which tool each goes to, their accepted forms with short examples, how to review the crosswalk, and
what people may still need to add.

This is new code (`faire_mapper.py`), developed from the `faire_mapper` prototype in the project.
It uses the full FAIRe checklist v1.0.2 (bundled) and needs only pandas and openpyxl. No language
model is used, as agreed; the tools are built so one can be added later (see below).

## Status

- Version 0.7.3. `planemo lint`: passes with no warnings. `pyflakes`: clean.
- Goes to Galaxy Australia as an early version with the wrapped FAIRe tools (decided 6 November
  2026). Each tool's help starts with a note saying so, which asks users to check the results and
  send problems to the Galaxy Australia help desk (to confirm with Galaxy Australia, question 8).
- `planemo test`: all tests pass in Galaxy 26.1 (summary at the end of this file); the five original
  tools' 37 tests also pass in Galaxy 25.0. The model tool needs Galaxy 25.1 or later, for its
  credentials.
- New on 7 November 2026, from Oliver's review: *FAIRe mapper: identify your files* says what each
  uploaded file looks like and where it goes; apply mapping says what a file in the wrong field looks
  like, stops when an OTU table has no read counts, warns when a final table has more sequences or
  reads than the raw one, and has a *Layout of this table* setting that overrides the detection
  ("Recognising the input files" below).
- Benchmarked on tables with known answers (see "How accurate is it?").
- Tried on four published eDNA datasets from Dryad and two from Australian studies, with
  independent answer keys (`dev/faire_mapper_real_datasets/`, `dev/faire_mapper_australian_datasets/`,
  summarised below), and end to end on CSIRO's SEA-MES data (`dev/faire_mapper_seames/`). Not yet
  tried on datasets from Australian labs that already have a FAIRe version.
- New in 0.7.3 (13 November 2026): propose mapping names the sample table as the user sees it in
  Galaxy (its dataset name) in the review sheet's *How to review*, the summary and the crosswalk's
  description, where it gave Galaxy's file name (dataset_N.dat). The Shiny app (`shiny/`) passes the
  name the same way.
- New in 0.7.2 (13 November 2026), from the FAIRe team's questions on 0.7.1:
  - The review sheet can be sorted or filtered (rows to review first, say). Apply mapping reads each
    decision with its input term, and lists the columns in the table's order; the replacement
    drop-down finds its list by the row's input term (Excel leaves drop-downs where they were when it
    sorts rows). A column whose row was deleted is kept as its own term, and the log says so. Tested
    with sorted and shuffled sheets, including headings that start with *. Tested in Excel too: a
    sheet sorted and saved there keeps its drop-downs, and apply mapping reads it.
  - The log says what happened to the rows with no decision: those with no proposed term and the
    matches for review are kept as their own terms (or the matches for review applied, with that
    option), and the mapper's accepted matches are applied.
  - *How to review* says where the rows come from, without naming the steps a workflow runs unseen:
    from the files provided, each row is one column heading (input term) of the sample metadata,
    named, the table with one row per sample. It says the values for the whole project (primers,
    protocols) are checked in the workbook's log.
  - The propose-mapping workflow (0.3) gives the review sheet as an output (datasets that aren't
    workflow outputs are hidden in the history), and the write-workbook workflow (0.2) takes it as its
    crosswalk input.
- New in 0.7.1 (13 November 2026), from the FAIRe team's second review:
  - The review sheet has a *Mapper's call* column (accept, review or no match), as in the
    walkthrough, and rows to review are shaded across the whole row.
  - *Things to decide* is now *additional checks to make*, in the review sheet and in propose
    mapping's output.
  - *How to review* says which table the rows come from: the table given to propose mapping, one
    row per sample, whose column headings are the input terms.
  - A MIxS or Darwin Core term is used by accepting it, never by rejecting: Reject always keeps the
    column as its own term. When the mapper proposes a FAIRe term for review and also found a MIxS
    or Darwin Core term for the column, that term comes first in the replacement list
    (*phosphate (MIxS term)*), and the reasoning says to choose Change and pick it.
  - The replacement list has a blank line between the best candidates and the rest.
  - *If rejected, kept as* says "your own term".
  - output_read_count is left empty for an OTU table that is rarefied (every sample with the same
    number of reads), as FAIRe asks for the reads that passed filtering; the log says so. Libraries
    with no column in the OTU tables (the SEA-MES 18S controls) have no counts, and the log says why.
- Also in 0.7.0, from the FAIRe team's review of the tools and outputs (13 November 2026):
  - **Review sheet.** Propose mapping writes a review sheet (Excel, `faire_mapper_review.py`) laid
    out as the team suggested: one row per column with the input term, the proposed FAIRe term, the
    score, the mapper's reasoning, the reviewer's decision (Accept, Reject or Change, from a
    drop-down) and the replacement FAIRe term (a drop-down with the column's five best candidates
    first, then every FAIRe term), plus what the column is kept as if the match is rejected. A
    rejected column kept its own name, or the name of a MIxS or Darwin Core term the mapper found
    for it (since 0.7.1, it always keeps its own term, and a MIxS or Darwin Core term is accepted
    or picked as the replacement). Hovering over a proposed term shows its definition. The workbook also
    has the additional checks to make, how to review, and the full crosswalk, which apply mapping uses to
    apply the decisions. Apply mapping takes the review sheet in place of the crosswalk; a row with
    no decision is applied as the mapper called it. On the SEA-MES 18S table, the review sheet with
    the trial's decisions gives the same workbook as the reviewed crosswalk.
  - **recordedBy and project_contact.** A project_contact given as a name and an email ("Bruce
    Deagle (bruce.deagle@csiro.au)") is written as the email, and the name goes to recordedBy, the
    people responsible for the dataset, when recordedBy is not given.
  - **Check before submitting.** The workbook's README sheet, the log and the help of apply mapping,
    FAIRe2ENA, FAIRe2NCBI and edna2obis: Darwin Core say to check the workbook before submitting.
  - **Term comments.** Each term's name in the workbook has a comment with its requirement level,
    description, example and field type, as FAIRe-ator makes them; user-defined fields say which
    column they came from.
  - **Several terms in one cell.** A cell of env_local_scale (or another term in "label [ID]" form)
    holding several terms joined by | is flagged in *additional checks to make* and the log, and the cells get
    a drop-down of the terms given, to pick one where one is meant.
  - **Read and sequence counts.** output_read_count, output_otu_num and otu_num_tax_assigned are
    filled for each library from the OTU and taxonomy tables (the final table of its assay), and
    input_read_count from a read count column of the library table (ENA's read_count). A table
    whose samples all have the same number of reads is reported as rarefied.
- New in 0.7.0 (13 November 2026), as Oliver Berry asked in his review of the SEA-MES 18S
  walkthrough: for a column with no FAIRe term, propose mapping suggests a MIxS or Darwin Core term
  whose name matches, for review, as the FAIRe guidelines ask for one before a made-up name. The
  terms come with the tool (`mixs_dwc_terms.tsv`, built by `dev/faire_mapper_other_terms/`), so
  Galaxy needs no web access: 745 MIxS terms (v7.0.1) and 95 Darwin Core terms (record-level,
  Event, Location and MaterialEntity terms of Simple Darwin Core) that FAIRe does not have, by name
  or by IRI. Every word of the column's name must match the term's name, or be a common word, so
  *Field bottle number* does not get fieldNumber. The crosswalk row has the term's own identifier
  (MIXS:0000505, dwc:year) and a comment saying what the term means, its MIxS unit and extensions,
  and what apply mapping will do. Once a reviewer confirms it, apply mapping names the user-defined
  field after the term and, for a MIxS number, adds the unit from the column name to each value
  (*Phosphate (uM)* becomes phosphate, 0.21 uM), as MIxS writes a number with its unit. These rows
  are applied only when confirmed, even with matches for review applied, and are kept when
  unmatched columns are left out. In the SEA-MES 18S table, Phosphate, Silicate, Pressure and
  Ammonia (ammonium, close) get MIxS terms; across the benchmark, Dryad and Australian tables, only
  the GOMECC table's four nutrient columns and *Sample_year* (Darwin Core year) do. Propose
  mapping's *Suggest MIxS or Darwin Core terms* (`--no_other_terms`) turns this off.
- New in 0.6.1 (13 November 2026): FAIRe terms that people often confuse, listed in
  `commonly_confused_terms.tsv` (group, term, meaning, the question that tells them apart). Propose
  mapping always marks a column matched to one of them for review, however strong the match. The
  crosswalk comment names the terms it is confused with and what each means, and asks the question;
  *additional checks to make* lists the column too, and apply mapping's log gives the same note for any of
  these terms in the values for the whole project. The groups, from Oliver Berry: the sampling
  depth (minimumDepthInMeters and maximumDepthInMeters, which go together) and the depth of the water
  column (tot_depth_water_col); the amount collected (samp_size) and the amount extracted
  (samp_vol_we_dna_ext); and the taxa the primers amplify (targetTaxonomicAssay) and the taxa the
  study set out to detect (targetTaxonomicScope). In the SEA-MES 18S trial, *Nominal depth* (the planned sampling depth) was
  proposed as tot_depth_water_col. `--confused_terms` gives another table.
  Also in 0.6.1: apply mapping keeps the dates as written in verbatimEventDate (FAIRe: "Sample
  collection date before formatting") when it converts them for eventDate, as Oliver Berry asked.
  Apply mapping writes checkls_ver as the checklist it's given defines it: the number 1 for v1.0.2,
  as before, or the version as text (v2.0.0, from the file name) for a checklist that defines it as
  text, as FAIRe checklist v2 will. A checkls_ver the submitter gives (in the values for the whole
  project, or a column) is kept as written, as Oliver Berry asked; text given for a checklist that
  defines a number is kept, with a warning that FAIRe-fier will report it.
- New in 0.6.0 (12 November 2026), from the day-night trial (`dev/faire_mapper_daynight/`): a
  column of times of day (Excel time cells, or 10:00, 4 pm) is proposed as verbatimEventTime, and
  apply mapping joins each time to its date in eventDate, with the UTC offset given on its form
  (*UTC offset of the times of collection*), or Z when the column's name says UTC, as FAIRe's
  eventDate is the date and time of sampling.
  When an OTU table's first column repeats (eDNAFlow's LCA output starts with its rank columns), the
  sequence IDs are taken from the column named as them (OTU, ASV, seq_id ...). Each OTU table can
  have a FASTA file of its sequences. A values file whose rows leave off empty fields at the end is
  read. A range (178-228) is accepted where the checklist allows one (ampliconSize). Controls are
  not given the project values FAIRe asks only of samples (the habitat terms), and their empty
  mandatory cells are written as "not applicable: control sample". The log's list of empty
  mandatory terms follows each term's condition (neg_cont_type for the negative controls only).
  Propose mapping has a new output, *additional checks to make*: what only a person can decide, each with
  what to do about it (a sample name used on more than one row, sample names that read as controls
  when no column marks the controls, columns with values only in the first rows, and times with no
  time zone). It lists them and changes nothing; the propose-mapping workflow gives it as
  *things_to_decide*. A plain list of fastq files, one per line with or without a header (as
  CSIRO's Data Access Portal lists a collection's files), works as a library table, and so do
  md5sum's checksum files and the CSV from PowerShell's Get-FileHash: the files are paired into
  libraries by their read number (R1 and R2), and *identify your files* names such lists as
  library tables. eventDate keeps the local time, which daily cycles follow: a time column whose
  name says UTC is converted to local time when the UTC offset is given, and *additional checks to make*
  lists UTC-only times. The offset can now be negative on the command line (`--utc_offset=-03:30`). A library name that already ends with the assay name
  (1A_16S_Fish) gets only the run added in lib_id, unless the library holds several assays.
- New in 0.5.1 (12 November 2026): each crosswalk comment says, in plain sentences and the same
  order, what the FAIRe term means (from the checklist), why it was proposed (with the table's own
  values), what apply mapping will do with the values, and, for rows to review, what to check. A
  yes/no control column explains why it goes to samp_category and how many rows become controls.
  Apply mapping writes `checkls_ver` as the number 1, as the checklist defines it and the FAIRe
  examples use it; the README sheet names the exact checklist. (From 0.6.1 it follows the
  checklist: text such as v2.0.0 when the checklist defines it as text, as FAIRe v2 will.)
- New in 0.5.0, from the SEA-MES trial: comment lines above the header (NCBI and ENA sheets) are
  skipped; MIxS lat_lon is split into decimalLatitude and decimalLongitude; one depth fills both
  depth terms; a yes/no control column goes to samp_category; dates saved at midnight lose the time;
  OTU tables named after fastq files (M108_S7_L001) are matched to samples, and sample details below
  the counts are left out; Eukaryota is not written to kingdom; date_ext is read as a date (the
  checklist gives it no format, but its example is an ISO date). PR2 and SILVA lineages give taxon
  names. Each OTU table is written as raw or final, so one assay can have both (an ASV table and
  its curated table); a final table without sequences takes them from the raw table where the reads
  show it is the same sequence, and curated names (*Trachurus Sp*, *Diaphus Sp1*) give their rank. Values for the whole project
  can name their assay, and go to that assay's projectMetadata column; the sheets get FAIRe-ator's
  drop-down lists; and OTU tables in long form (one row per sample and sequence) are read. From
  the Wilderlab table: a table that holds several assays is split by the column that gives each
  row's assay (Wilderlab's *target*), and the assay names can come from it; a repeated sample column
  is used once, with a warning; a name given with its rank (NCBI's) fills its rank term, *root* is
  no assignment, and *unclassified Paracalanus* is named Paracalanus; short sequences under a
  *sequence* header are read as sequences; and a depth range (250-350) fills the minimum and maximum
  depth. Final tables follow FAIRe's rule (5 November): an ASV table with a column of curated names
  gives raw tables with every ASV, taxaFinal with one row per curated ASV, and otuFinal with each
  taxon's reads summed under its most abundant ASV; a curated table with one row per taxon takes the
  sequence of the ASV each row is named after. PR2 rows say so in identificationRemarks, as FAIRe's
  rank terms are Linnaean. lib_id is one amplicon of a sample in one run, as FAIRe defines a library:
  the library name, assay_name and seq_run_id (M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12), so a
  library that holds several amplicons gets a lib_id for each. From the authors' answers (6
  November): sample columns that all carry a prefix (S_M108) are matched to samples without it, and
  a curated ASV table given as final, with the ASV table before curation as raw, gives only the
  final tables, with the sequences from the raw table; a curated name that reads as a common name
  (*Atlantic Salmon*) is reported and the taxon named from the rank columns. From the FAIRe authors
  (6 November): "missing: not collected" in a control is written as "not applicable: control
  sample". *Find
  primers* reads primer sequences written in a methods text (pairs in a sentence or row; pairs of
  the table among sequences listed out of order, as in text from a PDF; named forward and reverse
  primers on rows of their own), and the primer table has the 18S V4 pairs of Stoeck et al. 2010
  and the Australian Microbiome, and the laboratory names vert01, tele01, 1391f and EukBr. A lookup
  on a methods text takes about a second (it took about 40). *Apply mapping* takes **library
  tables** (ENA or SRA run reports, the SRA submission sheet, or a lab's run sheet) and fills
  experimentRunMetadata with library IDs, files, checksums and archive links. A word and its agent
  noun (sample, sampler) no longer match; this raised three benchmark scores slightly (below), and
  no score fell. The shortlist lists ten candidates when no term clearly leads (the fifth scores
  within 0.1 of the first), and five otherwise (6 November; `--shortlist_close`, results below).
- New in 0.4.0: several columns can build geo_loc_name, a number and its unit in one cell fill two
  terms, and **apply mapping** writes a FAIRe workbook that FAIRe-fier reads, with OTU and taxonomy
  sheets that FAIRe2MDT converts. *Propose mapping* can read a data dictionary (column
  descriptions) as well as the table. The review Interactive Tool is not built yet.

## Files

| File | Purpose |
|---|---|
| `faire_mapper.py` | The mapper: `profile` and `map` commands |
| `faire_mapper_adjudicate.py` | Answers review requests with a model, or checks answers given elsewhere (`faire_mapper_model.xml`) |
| `faire_mapper_methods.py` | Finds values for the uncovered FAIRe terms in methods text with a model, and checks them (not yet a Galaxy tool) |
| `faire_mapper_apply.py` | Writes a FAIRe workbook from a table and its reviewed crosswalk (`faire_mapper_apply.xml`) |
| `faire_mapper_otu.py` | Reads OTU or ASV tables and taxonomy tables for apply mapping |
| `faire_mapper_kinds.py` | Says what kind of input a table looks like (sample, OTU, taxonomy, library table and others) and where it goes |
| `faire_mapper_identify.py` | Reports on every uploaded file (`faire_mapper_identify.xml`) |
| `faire_mapper_library.py` | Reads library tables (run reports and run sheets) for apply mapping |
| `faire_primers.py` | Builds and updates primer tables, and finds primer pairs for names, citations or methods text (`faire_primers_find.xml`, `faire_primers_build.xml`) |
| `primers/faire_primers.tsv` | The bundled primer table (553 pairs) and its sources and update steps (`primers/README.md`). Most rows come from Takahashi et al. 2023 and keep its CC BY-NC 4.0 licence |
| `faire_mapper_identify.xml`, `faire_mapper_profile.xml`, `faire_mapper_map.xml`, `faire_mapper_apply.xml`, `faire_mapper_model.xml`, `macros.xml` | Galaxy tool definitions |
| `checklist/FAIRe_checklist_v1.0.2.xlsx` | FAIRe checklist, copied unchanged from FAIR-eDNA/FAIRe_checklist |
| `mixs_dwc_terms.tsv` | The MIxS (v7.0.1, CC0) and Darwin Core (CC BY 4.0) terms that FAIRe lacks, suggested for columns with no FAIRe term; built by `dev/faire_mapper_other_terms/build_terms.py`, with each standard's attribution at its top |
| `checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx` | FAIRe full template, as bundled with FAIRe-ator (the layout apply mapping writes) |
| `test-data/` | Test files (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the code in this folder. Bundled data keep their own licences: the checklist and full template are CC BY 4.0 (`checklist/LICENSE`), the primer table's sources are listed in `primers/README.md`, and `mixs_dwc_terms.tsv` names its sources and licences (MIxS CC0, Darwin Core CC BY 4.0) at its top |
| `checklist/LICENSE` | The FAIRe checklist's CC BY 4.0 licence |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

The benchmark is in `dev/faire_mapper_benchmark/` at the top of the repository, outside the tool
folder, so it is not published to the ToolShed.

## How it works

**Read.** Excel sheets, or text separated by commas, tabs, semicolons or bars (found from the first
rows, respecting quotes), in UTF-8, Windows-1252 or Latin-1. In text not separated by commas, decimal
commas (0,45) are read as points. With the header row left at 1, comment lines starting with # above
the header (as in NCBI and ENA submission sheets) are skipped; a # row with several cells, such as
QIIME's `#OTU ID`, is the header. The summary records how the file was read.

**Profile.** Each column is described from its values: share of numbers and their range and decimal
places; dates and their format (ISO, dd/mm/yyyy, dd.mm.yy, Excel dates and others), and integers that may
be Excel serial dates; DNA sequences and their
length; `label [ENVO:id]` values; "Country: region" place names; yes/no values; ISO and written
durations; sequence file names and whether they are read 1 or read 2; latitude and longitude in one
cell (MIxS lat_lon, "40.57773667 S 148.7301917 E", or "-33.85, 151.21"); and whether values are
unique per row or the same on every row. Units in headers, such as "(mL)" or "_um", are recorded. FAIRe
missing-value notes such as "not applicable: control sample" are treated as empty.

**Score.** Each column is scored against each FAIRe term that applies to the chosen assay type and
sample types (268 terms for water metabarcoding):

- *Header*: weighted word overlap with the term name and common names for it (280 common names for
  71 frequently used terms, kept in the code), after expanding about 100 abbreviations such as lat,
  temp, fwd and samp. Rare words
  count more than common ones.
- *Values*: how well the values fit the term's type, format and allowed values, taken from the
  checklist. A fit that is specific to few terms (latitudes, primer-length DNA, allowed values of a
  controlled vocabulary) counts more than a generic one (numbers). A clear mismatch, such as dates
  for a numeric term, rules the term out unless the header matches the term name exactly.
- *Level*: a column with one value for the whole table suits a project or assay-level term.
- *Description* (when a data dictionary is given): the column's description counts like a header.
  A term gets strong support when its name, or a common name of two or more words, appears in the
  description ("days frozen" in "number of days the water was frozen"), or when a one-word name opens
  it ("person" in "the person that filtered the sample"); a one-word name elsewhere gives weak
  support. When the description strongly names other terms but not the header's, the header match
  counts for less. Descriptions are read as written: only a few abbreviations are expanded (ID,
  temp), so "how long" is not taken for a longitude. Units in a description ("in litres", "(µm)") or
  a units column count as units in the header.

A data dictionary is either a table, with columns for the column name, the description and
optionally the units (headed, for example, *Variable*, *Description*, *Units*; or the first two
columns), or text with one line per column (`Days frozen: number of days ...`, Markdown bullets and
bold allowed). Lines and rows that name no column of the table are ignored, so a whole README can be
given. Descriptions also go into the *columns to review* for the model.

**Assign.** Each term goes to at most one column, best scores first. Unit columns follow the column
they describe: if `NO3` maps to `nitrate`, then `NO3 units` maps to `nitrate_unit`. Two exceptions:

- *Combined values.* geo_loc_name ("Country: region, locality") may come from several columns. A
  column whose best match is geo_loc_name joins the column that holds it when its score is at
  accept level, or when its values are INSDC country or sea names. The parts are ordered country
  first, then by fewer distinct values (broad to narrow), with headers such as *reef* or *region*
  first on a tie. A tie leaves the order a guess, so the parts go to review. A column that already
  holds whole values ("Australia: Queensland") keeps the term alone.
- *A number and its unit in one cell.* "1 L" is recognised as a quantity, so it fits samp_size, and
  the same column also fills samp_size_unit (unless another column holds the unit). For a term with a
  set unit, such as size_frac (µm), "0.2 micron" fits and the number is kept.
- *Latitude and longitude in one cell* fill decimalLatitude and decimalLongitude.
- *One depth.* A depth column fills minimumDepthInMeters and maximumDepthInMeters, unless its
  header or another depth column's says which end of a range it holds (*Min depth*, *Max depth*).
  FAIRe2NCBI takes `*depth` from maximumDepthInMeters.
- *A yes/no control column.* A column matched to neg_cont_0_1 or pos_cont_0_1 (project-level yes
  or no) whose values vary between rows says which samples are controls, so it goes to samp_category
  instead: yes is *negative control* (or *positive control*), no is *sample*. Apply mapping then sets
  neg_cont_0_1 to 1 and asks for neg_cont_type.

The crosswalk records these in two SSSOM extension columns, declared in its metadata block:
`combine_order` (1, 2, 3 for the parts of one value) and `value_part` (`number` or `unit`,
`latitude` or `longitude`, or `negative control if yes`). A column that fills several terms has one
row for each. An empty column whose header names a term is still matched (the benchmark counts
these), but writes nothing; apply mapping leaves empty unmatched columns out of the user-defined
fields.

**Route.** *Accept* when the score is high and clearly ahead of the alternatives; *review* when
plausible; *no match* otherwise. A column whose values vary is never accepted for a project-level
term, which holds one value. *Confirmed* columns come from a person's answers; *model* columns from a
model's answers (marked `"by": "model:<name>"`), which a person still needs to check. When the
answers give one term to several columns, the best-matching column keeps it and the others go to
review.

**Outputs.**

- *Mapping report*: one row per column with the proposed term, FAIRe sheet, route, score, evidence,
  reformatting hints, the shortlist, and the `combine_order`, `unit_term` and `also_fills` of
  combined and split columns.
- *Crosswalk*: in [SSSOM](https://mapping-commons.github.io/sssom/) TSV form, with a metadata block
  (valid YAML); confirmed answers are marked `semapv:ManualMappingCuration`. Accepted, confirmed and
  model matches are `skos:exactMatch`, matches for review `skos:closeMatch`.
- *Mandatory terms not covered*: what is left to find, in the methods text or from the data
  provider (the elicitation step). The assay type and checklist version are left out, since the
  tool settings supply them, as are terms only mandatory for the other assay type.
- *Columns to review*: model-agnostic requests, each with the column's values, profile and candidate
  terms (with descriptions, types and allowed values), and an instruction for the answer format.
- *Summary*: counts by route.

### Recognising the input files

`faire_mapper_kinds.describe` says what a table looks like, from its shape, headers and values, in
this order: a crosswalk (subject_id and object_id); text read as a table (the header is a sentence);
a sheet whose header is on a later row (most columns unnamed); a run report (SRR, ERR or DRR
accessions); an OTU table in long form; a library table (library names with sequence files, and
few sample details); a sample table (four or more columns of sample details, a column with a
different value on nearly every row, and not mostly counts); a primer table (a forward primer
column, primer sequences under a primer header, or two columns of primer-length sequences that
differ from row to row); a table of sequence files with few columns; an OTU table with samples as
columns (sample names as headers, or three or more columns of whole-number counts beside sequence
IDs, DNA sequences or names) or as rows; a taxonomy table (rank or lineage columns, no counts); a
data dictionary; values for the whole project (the first column holds FAIRe term names); and a
sample table with few details. Counts are judged on the top half of the rows, so sample details
kept below the counts do not hide them. Sample details are recognised by words (date, latitude,
depth, site, volume ...) and by the names and common names of FAIRe's sampleMetadata terms.

*FAIRe mapper: identify your files* reads every file (each Excel sheet on its own), finds the
sample tables first, and uses their sample names to recognise the OTU tables. It reports the kind,
the reasons, the field to give the file to and what to check next. On the test data, the
benchmark tables, the real and Australian datasets and the SEA-MES record (87 tables and texts,
counting each Excel sheet), 79 were named correctly: every sample table, OTU table, taxonomy table,
run report, crosswalk, dictionary, primer table and text. The other 8 are reported as not
recognised, with the reason: sheets of instructions or terms from SRA submission sheets (4), a
one-cell read-me (1), a list of PCR codes (1) and two sheets whose header is on a later row (2),
for which the report says to set the header row.

Apply mapping uses the same test when a file seems to be in the wrong field: it adds what the file
looks like, and the field it belongs in, to the message that stops the run (an OTU table that
matches no samples, or has no read counts; a library table with no library or file columns), and
warns when a taxonomy table has the samples' read counts. It also warns when a final table has more
sequences or reads than the raw table of the same assay, naming the 'Write this table as' setting;
a table with curated names, which gives both, is not compared with itself. *Layout of this table*
(detect, samples as columns, samples as rows, long form) overrides the detection; a layout that does
not fit the table stops with a message naming the setting, and a table whose headers and first
column both hold sample names gets a note naming it.

### Writing the FAIRe workbook (apply mapping)

`faire_mapper_apply.py` reads the table and the crosswalk, after the user has reviewed it (changed
`skos:closeMatch` to `skos:exactMatch` to confirm a match, edited a term, or deleted a row), and
writes a workbook in the layout FAIRe-ator makes from the bundled full template: README,
projectMetadata, sampleMetadata, the sheets for the assay type and the drop-down values, with the
same choice of fields by assay type, sample types and requirement levels. It converts values where
FAIRe needs a set form:

- dates to ISO 8601, reading day first or month first as the column's values show (13/09/2017), and
  stopping when nothing settles it unless the form says which; Excel dates and serial numbers;
- durations to ISO 8601 ("2 days", or 316 under a *Days frozen* header, become P2D and P316D);
- "1 L" into samp_size and samp_size_unit; "0.2 micron" into 0.2 for size_frac, converting mm to µm;
- MIxS lat_lon into signed decimalLatitude and decimalLongitude, keeping the digits given;
- a yes/no control column into samp_category (*negative control* or *sample*);
- dates saved with a time of midnight (as Excel and pandas write dates) to dates only;
- the parts of geo_loc_name into "Country: region, locality", with the country from the form when
  no column gives it;
- yes/no to 1/0; allowed values, including several joined with " | ", to the checklist's spelling;
- a project-level term mapped from a column with one value to projectMetadata.

Values for the whole project (a TSV of term and value, such as the methods values with status
*supported*) go to projectMetadata, or to every sample for a sample-level term; a column of the
table takes precedence. Unmapped columns are kept as user-defined fields. The log lists every column
written with an example, what was left out, values that could not be converted, and the mandatory
terms still empty.

OTU or ASV tables (`faire_mapper_otu.py`) become *otuFinal* and *taxaFinal* sheets, or *otuRaw* and
*taxaRaw*, as set for each table, named by assay when there are several, as in the FAIRe examples,
with samp_name as the column names, as FAIRe2MDT reads them. One assay can have a raw and a final
table:

- *Orientation* from the sample names: headers that match samp_name or lib_id, or are Illumina file
  names of them (M108_S7_L001 for M108), mean samples are columns; first-column values that match mean samples are rows, as in a published matrix of reads
  per taxon. With samples as rows, the counts end at the first column that is not counts or whose
  header is a sample-table column or exactly a FAIRe term name (*Site depth*); a repeat of the ID
  column (*Site.1*) is skipped.
- *Sequences*: an identifier column of DNA sequences (as DADA2 writes) becomes dna_sequence, with
  seq_id ASV1, ASV2 ...; a sequence column is read too.
- *Taxonomy*: from FAIRe columns, rank columns (Kingdom ... Species), a lineage string
  (`k__Animalia; p__Chordata; ...`, SILVA `D_0__`, or no prefixes), in the OTU table or a separate
  taxonomy table keyed by ID or sequence; confidence and percent identity columns too. With none,
  names in a matrix of reads per taxon are read as species (binomials), families (-idae), orders
  (-iformes), subfamilies (-inae, as "other: subfamily") or genera. scientificName and taxonRank are
  filled from the lowest rank where empty.
- *Names given*: a name column (scientificName, *LCA*, or a curated name such as *New_Name*) gives
  the rank as well. Binomials are species, and their genus replaces the genus column's (the curated
  name is often the current one, *Chrysophrys auratus* where the genus column has *Pagrus*); the log
  lists such names, so spelling mistakes can be caught. *Trachurus Sp*, *Diaphus Sp1* or *Thunnus
  albacares/obesus* are named to their first word and kept as written in verbatimIdentification. A
  single word takes the rank of the rank column holding it. Ranks below the name's are dropped.
  Two capitalised words whose first is in no rank column (*Atlantic Salmon*, a common name in the
  SEA-MES curated table) are not read as a name: the name is kept in verbatimIdentification, the
  rank columns name the taxon, and the log lists such names. Columns that are not taxonomy
  (*Common_Name*) are listed in the log.
- *Raw and final*: as FAIRe asks, the raw tables hold every ASV, taxaFinal lists every ASV of the
  final taxa (one per row), and otuFinal sums the reads of each taxon's ASVs under the ID of its most
  abundant ASV. An ASV table with a column of curated names (*Column of curated names*) gives all
  four. Given as the final table, with the ASV table before curation as raw, it gives otuFinal and
  taxaFinal only, and takes the sequences from the raw table. A curated table with one row per
  taxon, given as the final table of the assay, takes each
  row's dna_sequence from the raw table, by seq_id: the sequence of the ASV the row is named after.
  A row with more reads than that ASV, compared over every count column the two tables share, holds
  the reads of several ASVs (as in the SEA-MES 16S table); identificationRemarks says so, and the
  log asks for each ASV's curated name so taxaFinal can list them all. experimentRunMetadata gets one
  row per sample, assay and run, not one per table.
- Empty count cells are written as 0. Samples not in sampleMetadata are kept with a warning when
  they sit among the samples; columns of counts outside them are left out and listed. Rows below the
  counts that hold sample details (Sample ID, Voyage, Latitude ...), as the SEA-MES 18S table has,
  are left out and listed.
- The domain Eukaryota is not written to kingdom.
- *Linnaean ranks only*: FAIRe's taxonomy terms (kingdom to species) are Linnaean ranks, and FAIRe
  has no term for the classification a row follows, so the tool fills the rank terms fully only for
  Linnaean classifications, such as NCBI or BOLD taxonomy, whose names typically carry Linnaean
  ranks. For PR2 it keeps the genus and
  species, notes PR2 on each row, keeps the full lineage and leaves the higher rank terms empty;
  the user names PR2 and its version in otu_db. If FAIRe comes to support other classifications,
  this can change.
- PR2 and SILVA lineages without rank labels, as mothur and the Wang classifier write them
  (`Eukaryota(100);Obazoa(100);...`), are found by their column names (*PR2 tax*, *Silva 138.1 tax*,
  or a name ending in *tax*) and read by position. SILVA 138 gives the domain, then phylum to genus
  (and species). PR2 v5 has 9 levels and v4 8, and the levels between domain and genus (supergroup,
  division, subdivision, and a class, order and family that are often not Linnaean: Arthropoda is a
  PR2 class) are not written to FAIRe's rank terms; the genus and species are. An ASV named only
  above genus in PR2 gets that name as scientificName with taxonRank *other: PR2 subdivision* (or
  another PR2 level), and one named only as Eukaryota gets *other: domain*. Each row classified with
  PR2 gets "classified with PR2, whose levels above genus are not Linnaean ranks ..." in
  identificationRemarks. Placeholders
  (*Dinophyta_XX*, *Calanoida_fa*, *_unclassified*, *_sp.*) are skipped, and the classifier's
  confidence for the name given becomes confidence_score (100 as 1). The lineage is kept in
  verbatimIdentification. With several lineage columns, the first, or the one named on the form,
  gives the taxonomy, and the others go to identificationRemarks.
- When neither the table nor a library table gives the libraries, experimentRunMetadata gets one row
  per sample of each OTU table, with the assay name and a run ID from the form; samp_name stands in
  for the library name in lib_id (below), and the log says so.

Library tables (`faire_mapper_library.py`) say which sequence files belong to which sample: ENA's
read_run file report, the SRA's RunInfo, the SRA submission sheet (the first sheet that names
libraries or files is read), or a lab's run sheet. Columns are found by name (library_name or
library_ID, sample_name or sample_alias, filename and filename2, fastq_ftp or submitted_ftp with
their md5, run, sample and study accessions). A column of accessions under a sample heading
(RunInfo's *Sample*) is taken as the BioSample. Each library is matched to a sample by the sample
name column, or by its library name or file name starting with a sample name (M159_16SFish_LerayCOI
and M159_S7_L001_R1_001.fastq.gz both match M159); libraries of other samples are left out and
listed. Options keep the libraries whose name holds some text (16SFish), give the assays (one row per
library and assay when a library holds two assays' amplicons) and the run ID; otherwise the run ID
of the OTU table of the same assay is used. Each row gets lib_id, seq_run_id, filename, filename2,
checksum_filename, checksum_filename2 and associatedSequences (NCBI links for SRR, SAMN and PRJNA
accessions, ENA browser links for others, joined with " | " as FAIRe's example shows). FAIRe defines
a library as "an amplicon of a sample with unique MIDs", so lib_id is the library name, assay_name
and seq_run_id joined by underscores (M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12), unless the name
already ends with them. A library that holds the amplicons of several assays in one set of files (the
SEA-MES 16S and COI data) thus gets a lib_id for each amplicon, its rows sharing the files, and the
log lists such libraries; FAIRe2NCBI and FAIRe2ENA join them again and take the assay and run off,
so the archives get the library's own name. platform,
lib_layout and checksum_method go to projectMetadata when the libraries agree; the instrument is
reported for the user to add with its OBI ID. The library tables take the place of run columns in
the sample table, whose values fill what they do not give. ENA's fastq_ftp files are ENA's copies
(SRR33695780_1.fastq.gz), with their own checksums; the log says so.

Round trip: the CPR_2015 FAIRe example's otuFinal and taxaFinal, read back through the tool, give the
same counts and taxonomy (stray spaces trimmed; scientificName and taxonRank added where empty). Not
yet done: drop-down lists and cell comments in the sheets, ranks above a bare taxon name (edna2obis's
*match taxa* can fill them), and values that differ between assays (all go to *project_level*). `checkls_ver` is written as the number 1, which FAIRe-fier accepts (FAIRe-ator writes the file
name, which it does not).

### Adding a language model

The *columns to review* output is the request a model answers, and the *answers* input applies the
replies, so the model sits between two runs of the mapper without changing it.
`faire_mapper_adjudicate.py` does that step: it sends each request to a model, checks that each
answer is one of the column's candidates (anything else is discarded), and writes the answers file.
It can also check answers from a person or another model (`--answers_from`), or write the prompts
only (`--dry_run`). Standard library only.

It takes two request formats: Anthropic's (Claude; the API version `2026-10-21` and Bearer
authentication follow the current API reference) and OpenAI's, which OpenAI, LiteLLM gateways, vLLM,
Ollama and most other services accept. In OpenAI's format it sends only the model and the messages,
as some models refuse a temperature or a token limit. Keys are read from the environment only. A
refused key (401 or 403), a wrong address or model (404) or a service that cannot be reached stops
the run at once with a plain message; other errors discard that column's answer.

**As a Galaxy tool** (*FAIRe mapper: ask a language model*, added 6 November 2026, Galaxy 25.1 or
later). The user chooses where the answers come from:

- *The model this Galaxy server provides*: the server's job rules set four environment variables
  for the tool's jobs, so users need no key and the server controls the model and the cost. For
  example, in Galaxy Australia's job rules (TPV), with the key from the server's vault:

  ```yaml
  toolshed.g2.bx.psu.edu/repos/OWNER/faire_mapper/faire_mapper_model/.*:
    env:
      FAIRE_MAPPER_SERVER_FORMAT: openai          # or anthropic
      FAIRE_MAPPER_SERVER_URL: https://models.example.org/v1   # empty for the provider's public service
      FAIRE_MAPPER_SERVER_MODEL: model-name
      FAIRE_MAPPER_SERVER_KEY: "{{ vault_faire_mapper_model_key }}"   # leave out if none is needed
  ```

  When jobs run in containers, the same variables may also need the `docker_env_` or
  `SINGULARITYENV_` prefixes, as Galaxy Europe sets for LLM Hub. With none of them set, the tool
  stops and says the server provides no model.
- *My own model service*: the user fills in the tool's credentials (request format, address, model
  and API key), which Galaxy keeps encrypted in its vault and passes to the job as
  `FAIRE_MAPPER_USER_FORMAT`, `_URL`, `_MODEL` and `_KEY`. The data then go to that provider under
  the user's account, and costs fall on it.

The key never appears on the command line, so it is not in the job's parameters or command. As
Galaxy's documentation notes, credentials are in the job's script while it runs, where server
administrators can see them. *Only show what would be sent* writes the requests and names the
service and model, and sends nothing.

Tested here: request building in both formats, reply parsing, the key headers, the settings from
the environment (server and user), a self-hosted service without a key, the stop on a refused key,
a wrong address and an unreachable service, and the preview, all against a stand-in service on
this machine (12 checks), plus the tool's 5 Galaxy tests. Not yet tested against a real model
service, because this workspace cannot reach one.

**Test with a stand-in model.** A separate Claude worker answered 248 review requests from seven
benchmark tables, seeing only the requests (the same content a model would get), never the answers.
Its answers were applied with `--responses`:

| Table | Requests | First choice before | First choice after | Accepted correct after |
|---|---|---|---|---|
| Water agency (held out) | 23 | 90% | 96% | 100% |
| University lab (held out) | 25 | 90% | 94% | 100% |
| eDNA provider form (held out) | 23 | 91% | 96% | 100% |
| Provider form, messy values (held out) | 24 | 90% | 94% | 100% |
| Terse headers | 32 | 81% | 91% | 100% |
| Messy headers | 33 | 81% | 89% | 100% |
| No usable headers | 88 | 24% | 31% | 100% |

Of the 248 answers, the model fixed 39 of the mapper's errors and introduced 5. It left 94 of 98
distractor columns unmatched. Where the right term was among the candidates it chose it 95 times
out of 102 (93%). For 48 columns the right term was not among the five candidates, so no answer
could fix them; a longer shortlist for review columns is the obvious next step.

The stand-in reasoned over each request with more care than a single API call may, so treat these
as an upper estimate of what a model adds. Run `dev/faire_mapper_benchmark/run_with_answers.sh` with
real model answers to measure it properly.

### Values from the methods text

Much of FAIRe is not in sample sheets but in the methods: primers, target gene, filter, extraction
kit, PCR conditions, sequencer. `faire_mapper_methods.py` sends a model the methods text with the
mandatory and highly recommended terms the mapping did not cover (plus the primer names), and asks
for each value with a quote from the text. Each term goes as a short card from the checklist: its
name, whether it is a project or sample term, the description and type, and the allowed values,
format, unit and example where the checklist gives them (an example that repeats an allowed value is
left out). Sample identifiers (`samp_name`, `lib_id`) are not asked about, as each sample has its
own. Every answer is checked: the term must be one asked about,
the quote must appear in the text (ignoring case, spacing and quote marks), and the value must fit
the term (allowed values, 0 or 1, numbers; a measurement needs its unit). Values that pass are
*supported*; inferred values and values that do not fit go to *review*; the rest are discarded.
Controlled values are rewritten in the checklist's spelling. With `--primers`, primers the text
names or cites are looked up in a primer table and their sequences suggested for review; sequences
written in the text are suggested too, marked as stated, and named from the table when they match. Same modes
as the adjudication script:
`--model`, `--answers_from`, `--dry_run`. Methods in Word files need converting to text first (for
example with pandoc).

## How accurate is it?

### Method

Test tables were built from 60 rows of the GOMECC-4 generic FAIRe example (52 seawater samples, 8
controls): 51 sample-level fields, 10 run-level fields joined in by sample, and 9 assay-level values
repeated on every row, as lab sheets often do. Every table also has 25 distractor columns that should
not match anything (logistics, billing, QA). Columns are shuffled.

The column headers were written by two separate workers that did not see the mapper's code:

- **Set 1**: three styles (tidy, terse, messy), plus a version with messy values (dd/mm/yyyy dates,
  ENVO IDs removed) and a version with no usable headers (`col_1` ...).
- **Set 2 (held out)**: three organisations' styles (state water agency, university lab using R,
  commercial eDNA provider form), plus messy values. Written after set 1 was used for fixes, and not
  looked at until version 2 was frozen.

The mapper was committed before each set was opened (v1 before set 1, v2 before set 2), so the
first scores on each set are independent of the rules being tested.

Measures: *first choice*, the share of real columns given the right term; *shortlist*, the share
with the right term among the candidates (five, or ten when no term clearly leads; five before 6
November 2026); *accepted correct*, the share of *accept* routes that
are right; *distractors*, the share of distractor columns left unmatched.

### Results

Set 1, first scored with v1 (independent), then with v3 (after fixes made from set 1's errors):

| Table | First choice v1 | First choice v3 | Shortlist v3 | Accepted correct v3 (n) | Distractors v3 |
|---|---|---|---|---|---|
| Tidy headers | 89% | 93% | 97% | 98% (63) | 88% |
| Terse headers | 79% | 81% | 91% | 98% (47) | 80% |
| Messy headers | 74% | 83% | 93% | 98% (45) | 80% |
| Messy headers and values | 73% | 83% | 93% | 98% (44) | 84% |
| No usable headers | 1% | 24% | 41% | (1) | 100% |

Set 2 (held out), first scored with v2 (independent), then with v3 (after two bug fixes it exposed):

| Table | First choice v1 | First choice v2 | First choice v3 | Shortlist v3 | Accepted correct v3 (n) | Distractors v3 |
|---|---|---|---|---|---|---|
| Water agency | 89% | 90% | 90% | 97% | 98% (58) | 100% |
| University lab (R) | 89% | 84% | 90% | 97% | 100% (54) | 100% |
| eDNA provider form | 87% | 90% | 91% | 96% | 98% (56) | 100% |
| Provider form, messy values | 86% | 89% | 90% | 94% | 98% (55) | 100% |

Sanity check: with the original FAIRe column names, all 51 FAIRe columns map correctly.

Version 0.4.0 changes one benchmark result: the new common name *days stored* lets the terse
table's `days_stored` column be accepted (48 accepted, 98% correct); every other figure is the same.

On 5 November 2026 a word and its agent noun (*sample* and *sampler*, *sequence* and *sequencer*)
stopped counting as the same word, after the SEA-MES column *Sample* (fastq file names) was
accepted as the sampling device. First choice rose from 81% to 83% on both messy tables, the water
agency table left all its distractors unmatched (96% to 100%), one wrong suggestion in the Dryad
trials became no suggestion, and no score fell.

On 6 November 2026 the shortlist grew from five candidates to ten when no term clearly leads,
that is when the fifth scores within 0.1 of the first. On all tables with answer keys, 227 columns
went to review: five candidates held the right term for 152, ten would have held it for 166, and
this rule holds it for 162, with 37 lists longer than five (looser thresholds found at most 3
more, with twice as many long lists). First choices and accepted columns are unchanged. Shortlist
figures rose on five tables: terse headers 91% to 94%, both messy tables 93% to 96%, the water
agency table 97% to 99%, and the provider form with messy values 94% to 97%. The Dryad and
Australian results are unchanged: the terms missed there rank below ten (see 6b).

The changes between versions were general: keep mixed-case words such as pH whole (every pH column
failed in v1); match word stems (centrifuge, centrifugation); count a header that contains a term's
whole name; let strong value evidence reach *review* on its own; pair unit columns through term
names; treat FAIRe missing-value notes as empty; and keep "by" in names such as "collected by".

### Values from nine FAIRe example studies

The benchmark values above all come from one marine study. `build_cross_study.py` applies the same
held-out lab headers to the values of the nine example workbooks on the FAIR-eDNA site (plankton,
pond, reef, seamount and Gulf of Mexico metabarcoding; sediment and water qPCR). Across the 27
tables the first choice was right for 92% of columns (84 to 97%), the shortlist held the right term
for 98%, 98% of accepted columns were right (lowest 96%), and 98% of distractor columns were left
unmatched. So accuracy carries over to other studies' values; the drop on the Dryad deposits comes
from their headers and structure. The examples have no stated licence, so the derived tables are
not stored here; the script rebuilds them.

### On four published datasets

Four Dryad deposits (fish 12S from coral reefs, 16S from hypersaline lakes, 18S from groundwater
bores, fish 12S from Amazon streams), 85 columns, scored against answer keys from a separate curator
agent that never saw the mapper. Details and the per-dataset story are in
`dev/faire_mapper_real_datasets/README.md`.

| Run | First choice right (of 40 columns with a term) | Accepted columns right | Columns without a term left unmatched (of 45) |
|---|---|---|---|
| Mapper alone | 55% (58% in 0.4.0) | 78% (0.1.0), 84% (0.2.0), 85% (0.4.0) | 76% |
| With stand-in model answers | 78% | 89% (0.1.0), 94% (0.2.0 and 0.4.0) | 93% (91% in 0.4.0) |

0.1.0 could not read one table (semicolons, Windows-1252); 0.2.0 was changed after this trial, so its
figures here are not independent. The right term was in the shortlist for 88% of columns. The model
mainly helped by rejecting weak matches for study-specific columns and choosing between several
coordinate columns; it could not fix columns whose term was outside the shortlist. Values from the
methods text filled 5 to 26 terms per dataset, but primer sequences, ENVO terms, people and
identifiers were missing from all four. In 0.4.0 the Mathon country and site name columns build
geo_loc_name together, as the answer key suggests; that site name is the 0.4.0 drop in columns left
unmatched (the key gives geo_loc_name as acceptable for it).

### On two Australian datasets

Two studies with a sample table and a methods section: DiBattista et al. 2024 (Lizard Island, 72
filters, 14 columns) and West et al. 2021 (Kimberley, 71 sites, 9 columns). Details are in
`dev/faire_mapper_australian_datasets/README.md`.

| Run | First choice right (DiBattista, of 9) | Accepted columns right (DiBattista) | First choice right (Kimberley, of 5) | Accepted columns right (Kimberley) |
|---|---|---|---|---|
| 0.3.0, mapper alone | 4 | 5 of 6 | 5 | 6 of 6 |
| 0.3.0, with model | 5 | 5 of 7 | 5 | 7 of 7 |
| 0.4.0, mapper alone | 7 | 4 of 5 | 5 | 6 of 6 |
| 0.4.0, with model | 7 | 9 of 10 | 5 | 8 of 8 |

0.4.0 was changed after the 0.3.0 run, so its figures here are not independent; the benchmark
results did not change apart from one more accepted column (see the benchmark results above). The gains come from the combined place names, the number-and-unit cells and
the country names. The 0.4.0 rows were run before the data dictionary was added; with DiBattista's
Dryad README as the dictionary, and the common names *filter size* and *days frozen*, the first
choice is right for all 9 DiBattista columns and all 5 Kimberley columns, with and without the
model, and every accepted column is right (DiBattista 6 of 6 alone, 11 of 11 with the model;
Kimberley 7 of 7 and 8 of 8). These are the tables the changes were made for. **Apply mapping** wrote
a workbook for each study, which FAIRe-fier read with errors only for mandatory terms still empty,
`checkls_ver`, and habitat classes without ENVO IDs. The Kimberley matrix of reads per taxon (71
sites, 362 bony fish taxa) went in as otuFinal and taxaFinal sheets, and FAIRe2MDT converted the
workbook for GBIF's Metabarcoding Data Toolkit.

### On CSIRO's SEA-MES data

The 10 L sample sheet of the SEA-MES survey (Deagle et al. 2025), as submitted to NCBI, with 16S and
18S ASV tables and ENA's run report (`dev/faire_mapper_seames/README.md`). With 0.4.0 and no changes
for the dataset, 11 columns were accepted, all correct, once the header row was set by hand; the
trial found the gaps fixed in 0.5.0. With 0.5.0 the sheet maps as published: 12 accepted, all
correct, and with the control type added, 13. The workbook went through FAIRe-fier (sampleMetadata
passes), FAIRe2MDT, FAIRe2QIIME, FAIRe2NCBI and FAIRe2ENA. Compared with what the authors
submitted, 15 of 20 BioSample fields are identical and the other 5 differ only by the MIxS units
FAIRe2NCBI adds; the SRA table's library IDs, BioSamples, files and instrument match ENA's report
for all 288 libraries. The ASV table, with its preliminary BLAST and LCA taxonomy, is otuRaw and
taxaRaw; the authors' curated table of 235 fish taxa (reads summed per curated name) is otuFinal and
taxaFinal, with sequences for the 83 rows that hold one ASV.

The 18S data were run the same way, with a sample table made from the sample details below the
18S counts and 7 columns added from the ReadMe and the methods (202 samples, 44 columns, not seen
before): 21 accepted, of which 18 were correct; none of the 4 suggestions for review was right. The
errors: *Sample* (file names) matched *sampler* (fixed on 5 November: it now goes to review, and
20 are accepted); a column of station codes joined geo_loc_name; and *Filtered by* took recordedBy
from *Collected by*. After review, and with the primers and methods
from the report as values for the whole project, the 18S workbook went through every tool;
FAIRe-fier passed sampleMetadata and reported only `checkls_ver` in projectMetadata. With 0.6.0
(12 November), the 18S table's *Collection Time (UTC)* goes to verbatimEventTime and its times join
the dates in eventDate. As daily cycles follow local time, the trial gives the sites' UTC offset
(+10:00, AEST, off Victoria and Tasmania in July), and apply mapping converts the times to local time
(2023-07-07T00:45+10:00 for 14:45 UTC on 6 July). The table's *Collection Time (AEST)* column is an
hour ahead of AEST (22:48 for 11:48 UTC), so it is left out.

The COI table then joined the 16S workbook as a second assay (11,643 ASVs, not curated), with the
values that differ between the assays given an assay column. Every tool takes the two-assay
workbook, and the 16S outputs are unchanged. As each library holds both amplicons, the NCBI SRA
and ENA run tables have to be made once per assay for now.

### With a data dictionary

Two benchmark tables were described by a stand-in for a lab member (Claude Sonnet, as a separate
agent), who saw only the headers and six rows and wrote one plain-English description per column,
including the distractor columns (`dev/faire_mapper_benchmark/dictionaries/`).

| Table | First choice, no dictionary | First choice, with dictionary | Shortlist | Accepted (correct) | Distractors left unmatched |
|---|---|---|---|---|---|
| Terse headers | 81% | 91% | 91% to 100% | 48 (98%) to 56 (98%) | 80% to 88% |
| University lab (held out) | 90% | 94% | 97% to 99% | 54 (100%) to 58 (100%) | 100% to 100% |

The first run on these two tables gave 93% and 96%. One rule changed afterwards, prompted by a test
table rather than these (fewer abbreviations expanded in descriptions, so "how long" is not a
longitude), which gave the figures above. Real data dictionaries from Australian labs are the next
test.

### What the numbers mean

- **The *accept* route is reliable on the benchmark** (98 to 100% correct), less so on real
  deposits (84% without a model, 94% with one). The useful pattern is that a person reviews 7 to 20
  columns of a 95-column sheet, not all of them, and still glances at the accepted ones.
- **About 1 in 10 columns gets the wrong first choice**, but the right term is usually in the
  shortlist, so review is quick.
- **Values alone are weak.** With uninformative headers, only distinctive values (coordinates,
  primers, ENVO labels, dates, allowed values) are recognised.
- **Some "errors" are arguable.** "Collector initials" maps to `recordedBy` and "Weather notes" to
  `samp_weather`; both are real FAIRe terms, so these distractors were probably mislabelled. "Volume
  filtered" is used by labs for both `samp_size` and `samp_vol_we_dna_ext`.
- **Common names exist mainly for the fields tested.** The 280 common names were written for 71
  frequently used FAIRe terms, which overlap almost entirely with the 70 benchmark terms. The other
  FAIRe terms rely on their term names, so accuracy on less common fields will be lower than these
  figures. Real datasets will show which common names to add.
- **The test is easier than real life in two ways.** The values come from an already-FAIRe dataset,
  so controlled vocabularies are clean, and all the data are from one marine metabarcoding study.
  The headers were written by AI workers, not real labs. Real bespoke datasets are the next test.

## Upstream and related issues

- The FAIRe checklist and FAIRe-ator are CC BY 4.0 (licence files added upstream on 11 November
  2026). The checklist and full template are bundled here, as they are with FAIRe-ator, and the
  licence is copied in as `checklist/LICENSE`.
- The mapper code is MIT, the usual licence for Galaxy tools (as in the IUC's tools-iuc).

## Before deployment on Galaxy Australia

### Must do

1. **Test on real bespoke datasets** from CSIRO and partner labs, ideally ones that already have a
   FAIRe version, so the answers are known. Add them to the benchmark. (Four published Dryad
   datasets have been tried, with keys from a curator agent; keys from a FAIRe curator are still
   needed.)
2. ~~**Wait for the FAIRe checklist's licence file.**~~ Done 11 November 2026 (CC BY 4.0). The
   mapper code is MIT (decided 3 November 2026).
3. **Fill in `.shed.yml`** (owner) and the `<creator>` block in `macros.xml`.
4. **Publish to the Test ToolShed**, then ask Galaxy Australia to install it alongside the other
   FAIRe tools.

### Should do

5. **Extend apply mapping** (done in 0.4.0: the workbook, OTU and taxonomy tables; 0.5.0: library
   tables): add drop-down
   lists to the sheets, split values by assay, and read OTU tables in long format (one row per
   sample and ASV).
6. **Decide on model access** with Galaxy Australia (external service, locally hosted model, or
   none), including whether metadata may leave the server and who pays. The Galaxy tool (6 November
   2026) supports both a model the server provides and each user's own service, so the decision
   needs only configuration; then test it against the real service and run
   `dev/faire_mapper_benchmark/run_with_answers.sh` with that model's answers.
6a. ~~**Offer more candidates for review columns**~~ Done 6 November 2026: ten candidates when
   the fifth scores within 0.1 of the first, otherwise five (results above).
6b. **Let the model suggest a term outside the shortlist**, checked against the checklist and
   always sent to review: four of the six columns still wrong on the Dryad datasets needed this.
6c. **Tighten word matching and identifiers**: stop *sequencer* and *sampler* matching *sequence*
   and *sample*, and treat repeated values as a conflict for `samp_name`.
6d. **Fill common gaps from other sources**: ENVO terms checked against the ontology, and project
   details from the dataset's DOI record. Primers are covered by the bundled primer table
   (Takahashi et al. 2023, the metazoan and bacteria and archaea registers and the Wilderlab
   assay list, all confirmed for inclusion); add laboratory aliases. (The four Wilderlab-named
   pairs not in the current Wilderlab list were removed on 7 November 2026.)
7. **Build the review Interactive Tool**, so users can accept or correct mappings in the browser.
8. **Add a reuse library**: store confirmed crosswalks and offer one when a new table has the same
   columns.
9. **Grow the list of common names** from the real datasets in step 1, and re-run the benchmark
   after each change.
10. **Handle more combined columns** (geo_loc_name from several columns and "1 L" cells are done in
    0.4.0; latitude and longitude in one column, a depth range "250-350", and tables with an assay
    column in 0.5.0). Split PR2 and SILVA eukaryote lineages, whose ranks differ from FAIRe's, by
    rank name.
11. **Test the data dictionary on real ones** from Australian labs (reading them was added in 0.4.0,
    with the common names *filter size*, *days frozen* and region and place words for geo_loc_name,
    and a check that target_subfragment holds amplicon regions such as V4, not place names).

## Test data

- `messy_edna.csv`: the prototype's 5-row sample sheet (made up).
- `messy_edna_responses.json`: a reviewer's answers for two of its columns.
- `reef_stations_semicolon.csv`: 5 made-up rows in Windows-1252, separated by semicolons, with
  decimal commas and Excel serial dates.
- `apply_reef.csv` and `apply_reef.sssom.tsv`: four made-up samples from Lizard Island and a
  reviewed crosswalk, with country, reef and site columns for geo_loc_name, "1 L" and "500 mL"
  volumes, pore sizes in microns, dd/mm/yyyy dates, days frozen, a field blank and a notes column.
- `apply_project_values.tsv`: values for the whole project, one of them for review.
- `apply_dates_ambiguous.csv` and its crosswalk: two dates that fit day first and month first.
- `apply_reef_crosswalk_edited.xlsx`: apply_reef.sssom.tsv as a spreadsheet saves it (metadata lines
  in the first column, 1.0 as 1).
- `apply_reef_readme.md` and `apply_reef_dictionary.csv`: data dictionaries for apply_reef.csv, as
  README lines (every column) and as a table with units (six columns and one row that names none).
- `otu_asv_table.tsv`: four ASVs by the four apply_reef samples, with QIIME 2-style lineages and
  confidence values, and empty cells.
- `otu_by_sample.csv`: reads per taxon with samples as rows (one not in the sample table), and a
  *Site depth* column after the counts.
- `otu_dada2.tsv` and `otu_dada2_taxa.tsv`: three made-up sequences as row names, and DADA2-style
  rank columns keyed by sequence.
- `mixs_sheet.tsv` and `mixs_sheet.sssom.tsv`: the four apply_reef samples as an NCBI BioSample
  sheet would give them (comment lines, MIxS lat_lon, one depth, Control_Neg Y or N, dates at
  midnight), and its crosswalk from propose mapping with Control_Neg confirmed.
- `library_ena_report.tsv`: an ENA read_run report for those samples (made-up accessions), with a
  16S library to filter out, a library of another sample, and a run with a lone file beside its pair.
- `library_sra_sheet.xlsx`: the SRA submission sheet for the same libraries, with an instructions
  sheet first.
- `library_two_amplicons.tsv`: an ENA read_run report for two of those samples whose libraries
  (LIZ_01_16S_COI, LIZ_02_16S_COI) each hold two assays' amplicons in one pair of files. Made up.
- `otu_fastq_names.tsv`: an ASV table whose columns are Illumina file names (LIZ_01_S1_L001).
- `otu_long.csv`: an ASV table in long form (sample, ASV, sequence, taxonomy, reads, and a sample
  detail), with one repeated row. Made up.
- `otu_asv_curated.csv`: an ASV table in the form of `otu_raw_asv.csv`, with a *New_Name* column of
  curated names: two Sardinops ASVs under one name, and a bacterium with no curated name. Made up.
- `otu_asv_raw.csv` and `otu_asv_curated_names.csv`: one assay as an ASV table before curation
  (the ASVs of `otu_asv_curated.csv` and a human ASV) and the curated table of its fish ASVs, in the
  form of the SEA-MES 16S table the authors sent: rank columns, *New_Name* and *Common_Name*, no
  sequences, and sample columns with the prefix S_ (S_LIZ_01). Made up.
- `apply_reef_controls.csv` and `apply_reef_controls.sssom.tsv`: the reef table with a sample type
  column (sample or negative control) and "missing: not collected" in the field blank's depth and
  coordinates and in one sample's depth, and its crosswalk.
- `otu_wilderlab.csv`: a table in Wilderlab's layout for two assays (LG and RJ, in the *target*
  column), with a repeated sample column, NCBI names and ranks (*root*, *unclassified Paracalanus*,
  a clade), RJ sequences of 22 and 24 bases and a row with no assay. Made up, with real NCBI taxon
  IDs.
- `apply_reef_ranges.csv` and `apply_reef_ranges.sssom.tsv`: the reef table with one depth given as
  a range (12-15), and its crosswalk with the depth to both depth terms.
- `project_values_by_assay.tsv`: values for the whole project with an assay column: primers and
  target gene for COIElasmo and Fish16S, one value for the project, one for an assay not named.
- `otu_raw_asv.csv` and `otu_curated.csv`: one assay as a raw ASV table with sequences and
  preliminary taxonomy (a bacterium among the fish), and its curated table in the form of the
  SEA-MES 16S table (*New_Name*, *Common_Name*, reads summed per name): one merged row, one with the
  control reads removed, *Trachurus Sp*, *Diaphus Sp1* and a misspelt genus. Made up.
- `otu_pr2_silva.csv`: four zOTUs by the apply_reef samples, with PR2 and SILVA lineages and Wang
  classifier confidences in the form of the SEA-MES 18S table (lineages from that table; sequences
  made up).
- `apply_reef_times.xlsx`, `apply_reef_times.sssom.tsv` and `apply_reef_times_values.tsv`: four
  made-up reef samples, a field blank and an extraction blank in the layout of the day-night study's
  sheet (the time of collection in its own column of Excel time cells), their crosswalk, and values
  for the whole project and two assays (no trailing tabs, an amplicon size as a range). Made by
  `dev/faire_mapper_daynight/make_testdata.py`.
- `otu_lca_ranks.tsv` and `otu_lca_ranks.fasta`: an eDNAFlow LCA output (domain to species, the
  OTU column, then the samples) for those samples, and its ASV sequences. Made up, by the same
  script.
- `apply_checkls_ver.tsv`: values for the whole project that give checkls_ver as v2.0.0.
- `apply_times_utc.csv` and `apply_times_utc.sssom.tsv`: two samples with a *Collection Time (UTC)*
  column, as in the SEA-MES 18S table.
- `library_file_list.csv` and `library_md5sum.txt`: eight fastq files with made-up MD5s, as Windows
  PowerShell's `Get-FileHash -Algorithm MD5 | Export-Csv` writes them (a #TYPE line, then
  Algorithm, Hash and the full path) and as md5sum writes them, named with the assay at the end as
  the day-night study names its files (LIZ_01_Fish16S_R1.fastq.gz); and `library_file_names.txt`:
  their names only, one per line with a folder, as the Data Access Portal lists files. By the same
  script.
- `map_confused.csv`: six samples with a sampling depth (0, 5 and 10 m), the depth of the water at
  the site (15 and 22 m), the volume filtered (1 or 2 L) and the volume extracted (500 or 1000 mL).
- `map_other_terms.csv`: four samples with columns that FAIRe has no term for: *Phosphate (uM)*,
  *Silicate*, *Pressure (dbar)*, *Ammonia*, *Voyage* and *Field bottle number*. Made up.
- `apply_other_terms.sssom.tsv`: a reviewed crosswalk for that table: MIxS phosphate confirmed
  (MIXS:0000505), ammonium typed in with no object_id, silicate still for review.
- `review_table.csv`: four samples with a column the mapper wrongly matches (*Water phosphate*,
  for review as samp_size, with MIxS phosphate offered first in the replacement list), a MIxS term (*Silicate*), a column with
  no term (*Voyage*) and a depth. Made up.
- `apply_review_sheet.xlsx`: the review sheet propose mapping writes for that table, with decisions:
  Change to *phosphate (MIxS term)* for *Water phosphate*, Accept for *Silicate*, Change to
  tot_depth_water_col for *Depth (m)*, and Reject for *Voyage*. Its rows are sorted, rows to review
  first.
- `apply_review_sheet_undecided.xlsx`: the same sheet with no decision for *Depth (m)*, *Silicate*,
  *Voyage* and *Date*, one of each kind of row.
- `map_review.csv`: 11 rows in the form of the day-night study's sheet: a sample name used twice,
  a filtration control named but not marked, notes in the first rows of two columns, and times with
  no time zone.
- `primer_methods_sequences.txt`: a methods text with primer sequences: the TAReuk 18S V4 pair, an
  Illumina overhang, and a made-up pair on rows of their own.
- `survey_sheet.xlsx`: 15 rows of a held-out benchmark table (eDNA provider form style), on a sheet
  called *Samples* with a title row above the headers, and a second sheet. Values from the GOMECC-4
  generic FAIRe example in aomlomics/edna2obis (MIT).

## Running the tests and the benchmark

```bash
pip install planemo
planemo lint faire_mapper/
planemo test faire_mapper/     # run as an ordinary user, not root

# benchmark (needs pandas and openpyxl)
dev/faire_mapper_benchmark/run_benchmark.sh tools/faire_mapper/checklist/FAIRe_checklist_v1.0.2.xlsx
```

## planemo test results

Run on 4 November 2026 (version 0.5.0) with planemo 0.75.47 against Galaxy `release_25.0`, with
dependencies resolved through conda (python 3.12, pandas 2.2.3, openpyxl 3.1.5), and again on 5
November after the Wilderlab changes, the curated-name option and lib_id for each amplicon, and on
6 November after the changes for the authors' curated ASV table and the control rule, and after
the longer shortlists (propose mapping's first test checks a list of five and a list of ten). All 37
tests passed, and all 37 passed on GitHub on 6 November (Galaxy `release_26.1`, containers). On 6
November the model tool was added, with 5 tests (a preview with and without a service, the server
providing no model, own service without credentials, and an unreachable service, the last two
passing credentials as Galaxy would); all 42 tests passed in Galaxy `release_26.1` here. On 7
November the identify tool was added, with 2 tests, and 5 apply mapping tests for files in the
wrong field and the layout setting; all 49 tests passed in Galaxy `release_26.1` here. On 12
November (0.6.0) the day-night trial added 7 apply mapping tests, 3 propose mapping tests and 1
identify test; all 60 tests passed in Galaxy `release_25.0` here. 0.6.1 adds one propose mapping
test (commonly confused terms) and one apply mapping test (checkls_ver kept as given), and checks
apply mapping's note on the confused terms in an existing test. 0.7.0 adds two propose mapping tests
and one apply mapping test (MIxS and Darwin Core terms), and one of each for the review sheet; all 15
propose mapping, 35 apply mapping and 3 identify tests pass in Galaxy `release_25.0` here, and so does
the propose-mapping workflow test. 0.7.2 adds one apply mapping test (rows with no decision); all 15
propose mapping and 36 apply mapping tests pass in Galaxy `release_25.0` here, and so do both workflow
tests. 0.7.3 checks the table's name in an existing propose mapping test.

| Tool | Test | Checks | Result |
|---|---|---|---|
| profile | 1 | CSV: 10 columns described; latitude range, primer length and date format found | passed |
| profile | 2 | Excel sheet chosen by name, headers on row 2 | passed |
| map | 1 | CSV: latitude, date and primer accepted; primer flagged as project-level; a marker column with two values sent to review; notes left unmatched; SSSOM written; missing mandatory terms listed | passed |
| map | 2 | Excel, held-out headers: latitude and primer matched; columns to review written | passed |
| map | 3 | Reviewer's answers applied and recorded as manual curation | passed |
| map | 4 | Semicolon-separated Windows-1252 text: decimal commas and Excel serial dates read | passed |
| map | 5 | Sheet that does not exist: stops with the list of sheets | passed |
| map | 6 | Data dictionary as README lines: descriptions change two matches, reach the review requests and the report | passed |
| map | 7 | Data dictionary as a table with units: a person's name column goes to recordedBy | passed |
| find primers | 1 | Methods text: MiFish set, Bact16S_515F/806R inside longer names, a citation with its gene; "Forward" and "Reverse" ignored | passed |
| find primers | 2 | Names, with the user's table added: user's alias found, bad row left out, unknown names reported | passed |
| find primers | 3 | User's table only, with a gene filter | passed |
| find primers | 4 | Methods text with sequences: the TAReuk pair named from the table, a pair not in the table shown as written with its names and gene, an adapter ignored | passed |
| build primer table | 1 | User's rows added to the bundled table; bad row reported | passed |
| build primer table | 2 | New table from a register spreadsheet and a TSV; reused primer names reported | passed |
| build primer table | 3 | A correction row replaces the pair it corrects and records the change | passed |
| apply mapping | 1 | Reviewed crosswalk: geo_loc_name from three columns, "1 L" split, microns kept as numbers, dd/mm/yyyy dates read day first and kept as written in verbatimEventDate (since 0.6.1), days frozen as ISO durations, unmapped columns kept, a match for review left out, mandatory terms listed | passed |
| apply mapping | 2 | Matches for review applied, values for the whole project (one for review left out, one replaced by a column), two assays as projectMetadata columns, unmapped columns dropped | passed |
| apply mapping | 3 | Dates that fit both orders: stops and says which form setting to use | passed |
| apply mapping | 4 | The same dates read month first, as set on the form | passed |
| apply mapping | 5 | OTU table with samples as columns and lineages: otuFinal and taxaFinal written, empty cells as 0, confidence as numbers, run rows made with the run ID, samp_name standing in for the library name in lib_id | passed |
| apply mapping | 6 | Two assays: a reads-per-taxon matrix (samples as rows, sample details left out, names read as ranks) and a DADA2 table with its taxonomy joined by sequence, as otuRaw and taxaRaw sheets named by assay | passed |
| apply mapping | 7 | OTU table whose names match no sample: stops with the names found | passed |
| apply mapping | 8 | A crosswalk edited in a spreadsheet and saved as Excel | passed |
| map | 8 | NCBI BioSample sheet: comment lines skipped, MIxS lat_lon to both coordinates, one depth to both depth terms (for review since 0.6.1, as commonly confused), Control_Neg (Y or N) to samp_category | passed |
| apply mapping | 9 | The same sheet: coordinates split and signed, dates at midnight written as dates, controls as *negative control*; an ENA run report as the library table (filtered by name, a library of another sample and a lone file left out, files, MD5s and links written, lib_id with the assay and run added); an ASV table named after fastq files; since 0.7.0, input_read_count from the report's read_count, and the read and sequence counts from the ASV table | passed |
| apply mapping | 10 | The SRA submission sheet as the library table: the instructions sheet skipped, libraries matched by sample name | passed |
| apply mapping | 11 | Libraries that hold two assays' amplicons in one pair of files: a lib_id for each amplicon (library name, assay and run), the rows sharing the files, and the log listing the libraries | passed |
| apply mapping | 12 | PR2 and SILVA lineages with confidences: PR2 genus and species, a higher PR2 name with its rank, Eukaryota at domain level, confidence_score, SILVA kept in identificationRemarks | passed |
| apply mapping | 13 | The same table with the SILVA column chosen: phylum to genus, placeholders skipped | passed |
| apply mapping | 14 | One assay as a raw ASV table and a curated final table: four sheets; each final row takes the sequence of the ASV it is named after, and a merged row is noted and the missing ASVs reported; *Trachurus Sp* as the genus, kept as written; a misspelt genus reported; unused columns listed; one run row per sample | passed |
| apply mapping | 15 | An ASV table with a column of curated names: raw tables with every ASV, taxaFinal with one row per curated ASV, otuFinal with each taxon's reads summed under its most abundant ASV | passed |
| apply mapping | 16 | A curated ASV table as final, with the ASV table before curation as raw: sample columns read without their prefix (S_LIZ_01), otuRaw and taxaRaw with every ASV, taxaFinal with the curated ASVs and their sequences from the raw table, otuFinal with each taxon's reads summed under its most abundant ASV | passed |
| apply mapping | 17 | A control with "missing: not collected" in its depth and coordinates: written as "not applicable: control sample"; a sample's "missing: not collected" kept | passed |
| apply mapping | 18 | Two assays: primers for each assay in its projectMetadata column, an unknown assay skipped, drop-down lists in the sheets | passed |
| apply mapping | 19 | One table for two assays (Wilderlab's layout): split by its target column, assay names from it, a repeated sample column used once, NCBI names and ranks, short sequences; a depth range to the minimum and maximum | passed |
| apply mapping | 20 | An OTU table in long form: pivoted to one row per sequence, repeated rows added, sample details left out | passed |
| apply mapping | 21 | The sample table given as an OTU table: stops (no read counts), saying it looks like a sample table and where it goes | passed |
| apply mapping | 22 | A taxonomy table given as an OTU table: stops, saying it looks like a taxonomy table and where it goes | passed |
| apply mapping | 23 | Raw and final the wrong way round, and an OTU table given as the taxonomy table: a warning for each, naming the setting | passed |
| apply mapping | 24 | *Layout of this table* set to samples as columns: read as set | passed |
| apply mapping | 25 | *Layout of this table* set to samples as rows for a table with samples as columns: stops, naming the setting | passed |
| apply mapping | 26 | Day-night layouts: a time column joined to the dates in eventDate at +10:00; the habitat project values written as "not applicable: control sample" for the two controls, and the extraction blank's empty eventDate and geo_loc_name too; a values file with no trailing tabs; ampliconSize 178-228 accepted; no empty neg_cont_type reported for the samples; an LCA output with the OTU column after the ranks, its sequences from a FASTA file | passed |
| apply mapping | 27 | A time column named *Collection Time (UTC)*, with no offset given: joined to the dates with Z, and a warning that eventDate holds UTC, not local time | passed |
| apply mapping | 28 | The same UTC times with the sites' offset (+10:00): converted to local time, 14:45 UTC on 6 September as 2017-09-07T00:45+10:00 | passed |
| apply mapping | 29 | A negative offset with minutes (-03:30) reaches the tool as one argument: 2017-09-05T21:00-03:30 | passed |
| apply mapping | 30 | A list of fastq files with their MD5s as PowerShell's Get-FileHash and Export-Csv write it (a #TYPE line; Algorithm, Hash and the full Windows path): paired into four libraries by read number, file names without their folders, checksums written and checksum_method MD5, lib_id LIZ_01_Fish16S_reef_run1 (the assay not repeated) | passed |
| apply mapping | 31 | The same files as a list of names, one per line with their folder and no header (as the Data Access Portal lists them): read as a file list, paired, folders taken off, no checksum_method | passed |
| apply mapping | 32 | The same files as md5sum writes them (no header): read as a checksum list, paired, checksums written | passed |
| apply mapping | 33 | checkls_ver given as v2.0.0 in the values for the whole project: kept as written, with a warning that checklist v1.0.2 defines a number; since 0.7.0, a project_contact given as a name and an email split into recordedBy and project_contact | passed |
| map | 9 | Excel time cells in a Time column: verbatimEventTime (times of day), with a note that apply mapping joins them to the dates | passed |
| map | 11 | Times in UTC only: *additional checks to make* lists them, with how to get local time | passed |
| map | 12 | Sampling depth, water depth, volume filtered and volume extracted: all for review despite strong matches, each comment naming the terms it is confused with and the question that tells them apart, and all in *additional checks to make* | passed |
| map | 10 | A sheet in the day-night study's form: the *additional checks to make* list gives a repeated sample name, a filtration control not marked as a control, two columns of notes and the times with no time zone | passed |
| map | 13 | Columns with no FAIRe term: MIxS phosphate (with the unit from the column name), silicate, pressure and ammonium (close) for review, with MIxS identifiers and the curie map; Voyage and Field bottle number get none; the report's other_standard column and the summary's count | passed |
| map | 14 | The same table with *Suggest MIxS or Darwin Core terms* unticked: no MIxS rows | passed |
| map | 15 | The review sheet: its five sheets (Choices hidden), the mapper's call, the decision and replacement drop-downs, a MIxS term as a proposal, and a MIxS term first in the replacement list of a FAIRe match for review; since 0.7.3, the table named as Galaxy shows it | passed |
| apply mapping | 35 | The review sheet as the crosswalk, its rows sorted: Accept for a MIxS term, Change to the MIxS term offered for a wrong FAIRe match, Change to tot_depth_water_col, Reject keeping the column's own term, and the count of decisions in the log | passed |
| apply mapping | 36 | The review sheet with four rows left with no decision and matches for review applied: the log says what happened to each kind of row | passed |
| apply mapping | 34 | Confirmed MIxS terms name the user-defined fields with unmatched columns left out: phosphate with the unit added to each value (0.21 uM), ammonium typed in by the reviewer; silicate, still for review, left out and listed | passed |
| identify | 1 | Eight files: sample, OTU, taxonomy, library, dictionary, text, curated OTU table and crosswalk, each named with its reason | passed |
| identify | 2 | Two Excel files: each sheet on its own (the SRA sheet's library sheet, a primer register); no sample table found | passed |
| identify | 3 | A checksum file as md5sum writes it, and a list of file names with no header: library tables, not text | passed |
