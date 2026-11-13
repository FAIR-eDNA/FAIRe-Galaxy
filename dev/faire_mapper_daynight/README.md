# The FAIRe tools on the day-night eDNA study

A trial of the FAIRe mapper and the conversion tools on a published dataset in its authors' own
formats, from 12 November 2026: West K. M. et al. (2024) Continual day-night eDNA detectability
amidst diel reef species fluctuations on diver transects. *Environmental DNA* 6: e70018
(https://doi.org/10.1002/edn3.70018, CC BY). Three temperate reef sites in Tasmania, sampled every
6 hours over 24 hours (10 am, 4 pm, 10 pm and 4 am), ten 1 L samples per site and time, two assays
(16S Fish and COI Leray), sequenced on a NovaSeq 6000 at AGRF.

## Data

The reads and the files below are on CSIRO's Data Access Portal
(https://doi.org/10.25919/pzsq-kv47), under CC BY-NC 4.0. `demo/daynight` is a small copy (the 150
sequences of each assay with the most reads, with the licence and credit in its README), made by
`make_demo.py`; `DATA=demo/daynight run.sh OUTDIR` runs the trial on it in under half a minute. With
the full files, `run.sh` takes them from a folder given as `DATA`:

| File | What it holds |
|---|---|
| `Day_night_Tasmania_sample_data.xlsx` | 126 rows: sample ID, site, time, latitude, longitude, date, and three columns of notes (collectors, filterers, a short ReadMe) |
| `Day_night_16S_LCA_output.txt`, `Day_night_COI_LCA_output.txt` | eDNAFlow's LCA output: domain to species, then the OTU column (ASV_1 ...), then reads per sample. 3,215 16S and 18,817 COI ASVs |
| `Day_night_16S_ASV.fasta`, `Day_night_COI_ASV.fasta` | the ASV sequences (7,373 and 65,410; the LCA outputs list those with an assignment) |
| `West_2024.pdf` | the paper: methods in sections 2.1 to 2.3 and Table 1 |
| `fastq_file_names.txt` | the portal's list of the 478 fastq files, one per line with its folder (`16S_Fish_fastq_files/1A_16S_Fish_R1.fastq.gz`) |

The fastq ReadMe on the portal names the files `1A_16S_Fish_R1.fastq`, with the filtration controls
as `Filt_control_3_4_...` and the extraction blanks as `Extbl19_4_...` (taken on 19 April 2022).
Names rebuilt from that convention, a forward and a reverse file for each sample column of the two
LCA outputs, match 476 of the 478 files on the portal. The two that differ: the portal has no files
for any filtration control, though the 16S table has a column for Filtration control 1 + 2; and it
has files for a PCR blank, PCRbl19_4 (16S), which neither the sheet nor the OTU tables name. The
list has no checksums, which need the files themselves.

## What a person does before mapping (`prepare_table.py`)

Propose mapping's *things to decide* list (`review_list.tsv`) names each of these, with what to do;
the tools do not decide them.

- **A duplicated sample name.** The sheet has 8B twice; the second sits between 9A and 9C at Waubs
  Bay, and both OTU tables have a 9B, so it is renamed 9B. The list gives "8B (2 rows)"; only a
  person can know the right name.
- **Which rows are controls.** The six filtration controls are marked only by name ("Filtration
  control 1 + 2"), so the sheet gets a sample type column (sample or negative control) and a
  control type column (field negative). The 16S table also holds an extraction blank, Extbl19_4,
  which the sheet does not; it is added as an extraction negative. The PCR blank PCRbl19_4, which
  has only fastq files, is added as a PCR negative.
- **Notes and times.** The list also gives the three columns of notes (values only in the first
  rows) and the times with no time zone (answered by the UTC offset on apply mapping's form).

## Review (`reviewer_decisions.tsv`)

With the fixes below, one decision: delete *Collected by*, a list of the three collectors in the
first rows (propose mapping flags it, as recordedBy holds one value per project); recordedBy is
given as a project value. *Filtered by* and *Information:* (notes) have no FAIRe term and are left
out (`--drop_unmapped`).

## Values from the paper (`project_values.tsv`)

The primers, PCR, extraction, sequencing and bioinformatics from the methods, with a column for
each assay where they differ. *Find primers* finds both primer pairs from their sequences in
Table 1, including the inosines of jgHCO2198. The habitat terms (marine biome, marine subtidal rocky
reef, ocean water, from ENVO's current labels), the control types (field negative for the filtration
controls, extraction negative for the extraction blank), 9B for the second 8B and the UTC offset
(+11:00, Australian Eastern Daylight Time, which all three trips fell within) were the trial's
choices; Oliver Berry confirmed them on 12 November 2026, and PCRbl19_4 as a PCR blank on
13 November.

## What the trial found in the tools

The first run stopped or went wrong at each of these. Each was fixed with a test written first
(FAIRe mapper 0.6.0, FAIRe2QIIME):

| What happened | Fix |
|---|---|
| The time of collection, in its own column of Excel time cells, was proposed as *samp_store_dur* (storage duration), and eventDate held the date only. NCBI could not then tell the 10 am, 4 pm and 10 pm samples apart | Propose mapping recognises times of day and proposes verbatimEventTime (FAIRe's term for the time as written). Apply mapping joins each time to its date in eventDate (FAIRe: "the date and time of sampling", 2008-01-23T19:23-06:00), with the UTC offset given on the form |
| The LCA output's first column is *domain*, so apply mapping took it as the sequence ID and stopped ("seq_id repeats") | When the first column repeats, the ID column is the one named as one (OTU, ASV, seq_id ...) with a different value on every row |
| dna_sequence, mandatory in FAIRe, was empty: the sequences are in FASTA files | Each OTU table can have a FASTA file of its sequences |
| The project values file could not be read: rows without an assay had no trailing tab | Rows that leave off empty fields at the end are read |
| ampliconSize 178-228 was marked "not an allowed value" | A range is accepted where the checklist says one can be given |
| The project values for habitat (env_broad_scale, env_local_scale, env_medium) went to the controls too | Terms the checklist does not ask of controls ("mandatory unless samp_category = negative control ...") are written as "not applicable: control sample" for them |
| FAIRe-fier reported the extraction blank's empty eventDate and geo_loc_name | A control's empty mandatory cells are written as "not applicable: control sample" |
| The log listed neg_cont_type as empty in the 120 samples | The count of empty mandatory terms follows each term's condition |
| FAIRe2QIIME named its files 16S-not, from target_subfragment "not applicable" (the SEA-MES demonstration set too, since target_subfragment was added there) | FAIRe's missing-value terms are read as empty for the file names |
| The portal's list of fastq files, one name per line, was not read as libraries: the reader needs a header, and looked for the forward and reverse files on one row | A list of file names with no header is read, and the files are paired by their read number (R1 and R2). md5sum's checksum files and the CSV from PowerShell's Get-FileHash are read as they are, with the folders taken off the file names |
| lib_id repeated the assay (1A_16S_Fish_16S_Fish_AGRF_NovaSeq6000_SP), as the file names end with it | A library name that ends with the assay gets only the run added (1A_16S_Fish_AGRF_NovaSeq6000_SP), unless the library holds several assays |
| The decisions above were found by reading the sheet; nothing in the tools pointed a person to them | Propose mapping writes *things to decide*: repeated sample names, controls named but not marked, columns of notes, and times with no time zone, each with what to do |

## Result

With the prepared sheet and one review decision: 128 rows (120 samples, 6 filtration controls, an
extraction blank and a PCR blank), 88 FAIRe terms, both assays as otuFinal and taxaFinal with every sequence, and
no mandatory term left empty. experimentRunMetadata has 239 libraries (122 for 16S and 117 for
COI), every one on the portal, each with its two fastq files and lib_id
(1A_16S_Fish_AGRF_NovaSeq6000_SP). FAIRe-fier passes
both sheets (warnings only: coordinates with fewer than five decimal places). FAIRe2ENA writes 128
samples, with the collection times in local time (2021-11-01T10:00+11 for 10 am on 1 November). FAIRe2QIIME
writes metadata and manifests for both assays.

## Still to do

- **NCBI BioSample.** The ten replicates of each site and time have the same attributes, which NCBI
  does not allow; FAIRe2NCBI stops and asks for a field that tells them apart. A replicate column
  (A to J) in the sheet would do.
- **Checksums.** FAIRe2ENA's runs stop until each file has its MD5 checksum, as ENA checks the
  files against them. The reads are 13 GB, so the checksums are best made where the files are:
  AGRF's delivery may include an md5sum file, or `Get-FileHash -Algorithm MD5 *.fastq.gz |
  Export-Csv md5.csv` in PowerShell, in the folder of reads, writes one. Either goes to `run.sh` as
  `FILES` (and to apply mapping as a library table) as it is, in place of the list of names. With
  made-up checksums in an md5sum file, FAIRe2ENA writes an experiment and a run for each library.
- **ENA aliases.** FAIRe2ENA names each experiment and run by the lib_id without its assay and run.
  Here the library names end with the assay, so a library sequenced for one assay only becomes
  Extbl19_4, while the rest keep the whole lib_id (1A_16S_Fish_AGRF_NovaSeq6000_SP) so that 1A's
  16S and COI libraries differ. Both are valid, but keeping the lab's own name
  (Extbl19_4_16S_Fish) would be tidier.
