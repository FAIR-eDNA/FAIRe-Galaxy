# SEA-MES demonstration set

A small copy of CSIRO's SEA-MES eDNA data record, for demonstrating and testing the FAIRe tools in
Galaxy. It has the same files, with the same names, sheets, columns and layouts, as the published
record, but only 25 samples and the sequences with reads in them, and without the COI table (file
6), which the authors did not use. It is 0.5 MB (1.2 MB unzipped), against about 75 MB for the
record, and the whole trial runs on it in under a minute.

**This is not data for ecological analysis.** Totals, numbers of taxa and proportions differ from
the full record. Use the published record for any analysis.

## Source and licence

Deagle BE, Jayasinghe SA, Bessey C, Bodrossy L, West KM (2025). Environmental DNA data from the RV
Investigator South-East Australian Marine Ecosystem Survey (SEA-MES) voyages (IN2023_V05 and
IN2024_V03), version 2. CSIRO Data Access Portal,
[doi:10.25919/ngqx-3557](https://doi.org/10.25919/ngqx-3557). Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Raw reads: NCBI BioProject
[PRJNA1263580](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1263580/).

The methods texts are from the project's NESP final report (Deagle et al. 2025, CC BY 4.0), as in
`dev/faire_mapper_seames`. The ENA run report is ENA's public file report for the BioProject.

**Changes made** (as CC BY 4.0 asks): file 6 left out, rows and columns removed as below, files 7 and 8 gzipped,
the 18S table's *Total reads* recalculated for the samples kept, and the formulas of the 18S SRA
sheet (library_ID and the file names) written as their values. Nothing else was edited.
`dev/faire_mapper_seames/make_demo.py` makes the set from the full record, so the cut can be
checked and repeated.

## Samples kept

| Set | Samples | Why |
|---|---|---|
| 10 L | M097, M099, M100 (CTD32), M106 to M109 (CTD35), M153 to M156 (CTD50) | In every file: surface, chlorophyll maximum and a pair of bottom samples at three stations |
| 10 L field controls | M056, M172 | Controls with 16S and Wilderlab reads |
| Deep-tow | CN021, CN022, CN065, CN066, CN165, CN166 | Three pairs (Mini Bongo and OCD water, sites S4.1, S11.3 and N18); Wilderlab's table names the N18 pair CN065 and CN066 a second time (the authors confirmed they are CN165 and CN166) |
| 2 L | S029, S030, S035, S036 | In the 18S and Wilderlab tables |
| 2 L, no details | S099 | In Wilderlab's table only, with no sample details anywhere in the record |
| Milli-Q control | MQ1 | In Wilderlab's table only, not in any sample sheet: 5 L of Milli-Q water filtered on the ship (a field negative) |
| 18S controls | NTC-7C-1608411, ATCC1010-652C-1608410 and Soil-204C-1608412, each on runs BOD14795 and BOD14856 | Control libraries sequenced with the 18S samples (a no-template control, a mock community and a soil sample): reads at the archive, not in the 18S table. Kept in the run report and the SRA sheet (since 13 November 2026) |

Sequences with no reads in these samples are left out, except the ASVs the kept curated 16S rows
are named after. The 18S and Wilderlab tables keep the 300 sequences of each assay with the
most reads in these samples; the 16S tables are kept whole for them.

The authors' ASV-level table of curated 16S names is not published yet. When it is in the trial's
`data/private` folder, `make_demo.py` cuts it the same way into `private/` here, which is kept out
of the repository; the trial then takes the final 16S tables from it, and from file 5 without it.

## Files

| File | Here | What it shows the tools doing |
|---|---|---|
| `1_SEA-MES_M_samples_metadata_10L.xlsx` | 13 10 L samples, as the NCBI BioSample sheet | Skipping the 11 comment lines above the header; splitting MIxS *lat_lon*; a Y/N control column read as samp_category |
| `2_SEA-MES_CN_samples_metadata_OCD.xlsx` | 6 deep-tow samples, 106 columns, most empty | Empty columns with FAIRe names; *lat_lon* with a redundant minus sign ("-41.844061 S") |
| `3_SRA_metadata_SEAMES_18S.xlsx` | The SRA sheet's rows for these samples and the 18S controls, formulas as values | What the authors submitted for 18S, to compare with FAIRe2NCBI's SRA table |
| `4_SEA-MES_16S_ASV_level_output_with_seq.csv` | 310 16S fish ASVs, sequences and preliminary BLAST taxonomy | The raw table (otuRaw and taxaRaw) |
| `5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv` | 48 curated fish taxa, reads summed per name, no sequences | The final table: each row takes the sequence of the ASV it is named after; 29 rows sum several ASVs; names such as *Trachurus Sp* |
| `7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz` | 300 18S zOTUs for 15 samples, PR2 and SILVA lineages | Fastq file names as column headers; 37 rows of sample details below the counts; PR2 ranks |
| `8_WL_Full_SEA_MES_samples.csv.gz` | 2,862 sequences from Wilderlab's 12 assays, for 25 samples | One table for 12 assays (the *target* column); repeated column names, renamed by the trial as the authors confirmed; NCBI names and ranks, with *root* for no assignment |
| `filereport_read_run_PRJNA1263580.tsv` | ENA's run report rows for these samples' 35 libraries and the six 18S control libraries | The library table: file names, checksums and accessions; each 16S library also holds the unused COI amplicons |
| `ReadMe_Description.md`, `dublincore-000065684v002.xml` | The record's ReadMe and metadata, unchanged | Values for the whole project (assays, primers, sequencing runs) |
| `methods.txt`, `methods_consolidated.txt` | The report's methods, unchanged | Find primers and the methods step |

## Running it

Every step of the SEA-MES trial runs on the set:

```bash
DATA=demo/seames RSCRIPT=/path/to/Rscript dev/faire_mapper_seames/run.sh OUTDIR
```

In Galaxy, upload the files and follow `dev/faire_mapper_seames/README.md`, step by step.

## What you should see

From the run on 6 November 2026 (mapper 0.5.0), with the private table:

- **Propose mapping**, 10 L sheet as published: 12 columns accepted, all correct, 5 for review.
  With the control type added and reviewed, the workbook has 13 samples and 54 FAIRe terms.
- **16S**: the ASV table as raw and the authors' curated ASV table as final for Fish16S: taxaFinal
  lists the 268 curated ASVs with their sequences, and otuFinal the 48 taxa, 29 of them summing
  several ASVs; 13 library rows from the run report, each with a lib_id such as
  M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12. Without the private table, file 5 gives the 48 taxa,
  each with the sequence of the ASV it is named after.
- **FAIRe-fier**: sampleMetadata passes; projectMetadata has `checkls_ver` (the known FAIRe-ator
  format) and recordedBy (not in the files).
- **FAIRe2NCBI**: 13 BioSamples, with 15 of 20 fields identical to the authors' sheet and the other
  5 the same values with MIxS units; 13 SRA rows, one per library, matching ENA's report. **FAIRe2ENA**: 13 experiments and runs.
- **18S**: a sample table made from the details below the counts (15 samples); 15 SRA rows matching
  ENA's report and the authors' SRA sheet. Since 13 November 2026 the table also has the six control
  libraries (a row each, from the run report), so the workbook has 21 samples, FAIRe-fier passes,
  and the 21 SRA rows match ENA's report; the authors' sheet names the controls' libraries
  differently (NTC_18S).
- **Wilderlab**: 25 samples from the three sets, with the second CN065 and CN066 renamed CN165 and
  CN166; the table split into 12 assays; *root* rows left unnamed. FAIRe-fier reports 9 errors in
  sampleMetadata, all for S099 and MQ1, which have no details in the record (MQ1's date and place). FAIRe2MDT makes a
  workbook for each assay. FAIRe2QIIME writes 7 files for 12 assays, as assays of the same gene
  overwrite each other (an upstream problem).
