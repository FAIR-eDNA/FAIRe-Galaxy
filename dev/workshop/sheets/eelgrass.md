# Nova Scotia eelgrass: the least a metabarcoding dataset needs

A COI metabarcoding study of invertebrates in eelgrass (*Zostera marina*) meadows at 17 sites across
Nova Scotia, Canada, sampled in 2019 and 2023 (Trask et al., Dryad, CC0). The published files are a
table of reads per species and sample, and the coordinates of each site. There is no sample table, no
controls, no sample dates and no sequence behind each species name.

This exercise shows what can still be made FAIR from such files: a FAIRe workbook that passes
FAIRe-fier, and presence records for GBIF. It also shows what is lost when the sequences are not
published with the identifications.

## The files

You don't need to download anything for the exercise: the app loads the files itself. They are here
to look at, and for *Doing the preparation yourself* at the end. To download one, open it and press
*Download raw file* at the top right.

- As published on Dryad ([`demo/eelgrass`](../../../demo/eelgrass), with the source and licence in its
  README): the species table
  [`Final_ASVTable_withTaxonomy_Filtered.csv`](../../../demo/eelgrass/Final_ASVTable_withTaxonomy_Filtered.csv),
  the site coordinates [`Site_coordinates.csv`](../../../demo/eelgrass/Site_coordinates.csv) and
  [`Dryad_README.md`](../../../demo/eelgrass/Dryad_README.md).
- Prepared for the app ([`shiny/demo/eelgrass`](../../../shiny/demo/eelgrass)): the sample table a person
  makes from them ([`eelgrass_samples_prepared.csv`](../../../shiny/demo/eelgrass/eelgrass_samples_prepared.csv)),
  a taxon table ([`eelgrass_taxa.tsv`](../../../shiny/demo/eelgrass/eelgrass_taxa.tsv)), and
  [`eelgrass_notes.md`](../../../shiny/demo/eelgrass/eelgrass_notes.md), the details the README leaves out,
  each with its source.

## Before you start

You need R (4.1 or later), Python (3.10 to 3.13) and the FAIRe tools app. To install the app, paste
this line into the R console (in RStudio, the *Console* tab) and press Enter:

```r
source("https://raw.githubusercontent.com/FAIR-eDNA/FAIRe-Galaxy/main/shiny/start.R")
```

The first time takes about 15 minutes, as it downloads the packages the tools need. After that the
same line starts the app in your web browser in a few seconds, and updates it first when a newer
version is out. If your organisation blocks
installers, ask your IT support before the workshop.

## The exercise

1. On the app's **Start** page, choose **Nova Scotia eelgrass** and press *Load the demonstration
   data*. (Or download the prepared files and add them yourself with *Add files*.)
2. **1. Make a workbook, FAIRe mapper, a. Your files**: run it. Which file is the OTU table? Why does
   it say the reads are summed per taxon?
3. **b. Propose a mapping**: run it on `eelgrass_samples_prepared.csv`, with `Dryad_README.md` as the
   data dictionary.
4. **c. Review the mapping**: Reject *Replicate* (FAIRe's biological_rep is the number of replicates
   for the whole project), then save the review. *Fill in the authors' answers* does this for you.
5. **d. Methods and project values**: the values for the whole project start empty. Open *1. Find the primers* and run *Find
   primers* on `Dryad_README.md` alone first. It names only "the Leray et al. (2013) primer set": how
   many published pairs fit that? Then run it on the README and `eelgrass_notes.md`, which gives the
   sequences in the authors' QIIME 2 script. Add the exact match, renaming its assay *LerayCOI*, and
   check what it adds in the table on the right: is Sabella spallanzanii the right target taxon?
   Then go on to *2. Find the other method details*: the reliable values come ticked. Check sequencing_location against the
   notes, and add them. In step 3, give the mandatory terms still missing in their fields.
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

Start from the published files and make the sample table in Excel: one row per sample column of
`Final_ASVTable_withTaxonomy_Filtered.csv` (CAB-1, CAB-2 ...). Add the site name, its latitude and
longitude from `Site_coordinates.csv` (WRK02 is Wreck Cove, WRK), the date range from the Dryad
README, the country and province, and ENVO terms. Then compare yours with
[`eelgrass_samples_prepared.csv`](../../../shiny/demo/eelgrass/eelgrass_samples_prepared.csv).
