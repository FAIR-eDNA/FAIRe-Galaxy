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

The fastq ReadMe on the portal names the files `1A_16S_Fish_R1.fastq`, with the filtration controls
as `Filt_control_3_4_...` and the extraction blanks as `Extbl19_4_...` (taken on 19 April 2022).

## What a person does before mapping (`prepare_table.py`)

- **A duplicated sample name.** The sheet has 8B twice; the second sits between 9A and 9C at Waubs
  Bay, and both OTU tables have a 9B, so it is renamed 9B. Propose mapping notes that the values
  repeat, and apply mapping logs "samp_name repeats ('8B')"; neither can know the right name.
- **Which rows are controls.** The six filtration controls are marked only by name ("Filtration
  control 1 + 2"), so the sheet gets a sample type column (sample or negative control) and a
  control type column (field negative). The 16S table also holds an extraction blank, Extbl19_4,
  which the sheet does not; it is added as an extraction negative.

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
choices; Oliver Berry confirmed them on 12 November 2026.

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

## Result

With the prepared sheet and one review decision: 127 rows (120 samples, 6 filtration controls and
1 extraction blank), 88 FAIRe terms, both assays as otuFinal and taxaFinal with every sequence, and
no mandatory term left empty. FAIRe-fier passes both sheets (warnings only: coordinates with fewer
than five decimal places). FAIRe2ENA writes 127 samples, with the collection times in UTC
(2021-10-31T23:00Z for 10 am on 1 November). FAIRe2QIIME writes metadata and manifests for both
assays (the manifests need the read file names; see below).

## Still to do

- **NCBI BioSample.** The ten replicates of each site and time have the same attributes, which NCBI
  does not allow; FAIRe2NCBI stops and asks for a field that tells them apart. A replicate column
  (A to J) in the sheet would do.
- **Library table.** A list of the 400-odd fastq files with their MD5 checksums would fill
  experimentRunMetadata (file names and checksums) and allow FAIRe2ENA's runs and FAIRe2NCBI's SRA
  table. The reads are 13 GB, so the list is best made where the files already are, and only the
  list (a few tens of KB) brought here. The other extraction blanks, which the OTU tables do not
  hold, could then be added from their file names (Extbl19_4 and the like).
