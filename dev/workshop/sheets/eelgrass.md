# Nova Scotia eelgrass: the least a metabarcoding dataset needs

A COI metabarcoding study of invertebrates in eelgrass (*Zostera marina*) meadows at 17 sites across
Nova Scotia, Canada, sampled in 2019 and 2023 (Trask et al., Dryad, CC0). The published files are a
table of reads per species and sample, and the coordinates of each site. There is no sample table, no
controls, no sample dates and no sequence behind each species name.

This exercise shows what can still be made FAIR from such files: a FAIRe workbook that passes
FAIRe-fier, and presence records for GBIF. It also shows what is lost when the sequences are not
published with the identifications.

## What is in this folder

- `published/`: the species table, the site coordinates and the Dryad README, as published.
- `prepared/`: the sample table a person makes from them, the project values and a taxon table, with
  the published files. The app's demonstration loads these.
- `README.md`: the source and licence.

[[COMMON]]

## The exercise

1. On the app's **Start** page, choose **Nova Scotia eelgrass** and press *Load the demonstration
   data*. (Or add the files in `prepared/` yourself with *Add files*.)
2. **1. Make a workbook, FAIRe mapper, a. Your files**: run it. Which file is the OTU table? Why does
   it say the reads are summed per taxon?
3. **b. Propose a mapping**: run it on `eelgrass_samples_prepared.csv`, with `Dryad_README.md` as the
   data dictionary.
4. **c. Review the mapping**: Reject *Replicate* (FAIRe's biological_rep is the number of replicates
   for the whole project), then save the review. *Fill in the authors' answers* does this for you.
5. **d. Methods and project values**: run *Find primers* on `Dryad_README.md`. It names only "the
   Leray et al. (2013) primer set". How many published pairs fit that? The project values give the
   pair the authors' pipeline used.
6. **e. Write the workbook**: the species table is filled in as otuFinal. Write the workbook and read
   its warnings.
7. **2. Check**: run FAIRe-fier.
8. **3. Convert, GBIF and OBIS (presence and absence)**: write the Darwin Core archive.

## What to look for

- The study published no sample table. Open `eelgrass_samples_prepared.csv`: every column came from
  the species table's column names, `Site_coordinates.csv` or the Dryad README. Which values are the
  same for every replicate of a site?
- eventDate is a period (2019-07/2019-09), not a day. What does that do to the records' usefulness?
- The workbook says dna_sequence is empty for all 138 taxa, and seq_run_id has no value. Where
  would these come from? (The raw reads are in NCBI BioProject PRJNA1145319.)
- The archive has 869 presence records. Two taxa are named only to the genus. Look at
  verbatimIdentification for them.
- Without sequences, can anyone check or redo these identifications as reference databases improve?
  Compare the SEA-MES demonstration, which publishes a sequence for every ASV.

## Doing the preparation yourself

Start from `published/` and make the sample table in Excel: one row per sample column of
`Final_ASVTable_withTaxonomy_Filtered.csv` (CAB-1, CAB-2 ...). Add the site name, its latitude and
longitude from `Site_coordinates.csv` (WRK02 is Wreck Cove, WRK), the date range from the Dryad
README, the country and province, and ENVO terms. Then compare yours with
`prepared/eelgrass_samples_prepared.csv`.
