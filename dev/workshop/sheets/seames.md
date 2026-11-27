# SEA-MES: a full metabarcoding dataset

Thirteen 10 L water samples (two of them field controls) from CSIRO's RV Investigator, from the
South-East Australian Marine Ecosystem Survey (Deagle et al. 2025, CSIRO Data Access Portal, CC BY
4.0). The files are a small cut of the published record. They hold:

- the sample sheet;
- a 16S fish ASV table with a sequence and preliminary taxonomy for each ASV;
- the authors' curated fish taxa;
- ENA's report of the sequencing runs;
- the methods, and notes on the record's contact and licence.

This exercise fills every sheet of a FAIRe workbook and runs every conversion: NCBI, ENA, GBIF, OBIS
and QIIME 2.

## The files

You don't need to download anything for the exercise: the app loads the files itself. They are in
[`shiny/demo/seames`](../../../shiny/demo/seames), whose README gives the source, the licence and the
changes made. To download one, open it and press *Download raw file* at the top right.

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

1. On the app's **Start** page, choose **SEA-MES** and press *Load the demonstration data*.
2. **Make a workbook, FAIRe mapper**: run *a. Prepare your files*, then *b. Map sample information* on
   `SEA-MES_10L_samples.csv`.
3. **c. Review the matches**: decide the six rows for review, then save. Suggested answers:
   - Accept Control_Neg as samp_category, *depth, and samp_vol_we_dna_ext;
   - Reject replicate, bioproject_accession and Location.

   *Fill in the authors' answers* does this for you.
4. **d. Methods and project information**: the values for the whole project start empty. Open *1. Find the primers* and find primers in
   `methods.txt` and the notes: two pairs match exactly. Which one goes with these data? Add it, and
   check its ampliconSize. Go on to *2. Find the other method details*: the reliable values come ticked. Add them, then
   look through the others. In step 3, give the mandatory terms still missing in their fields.
5. **e. DNA results and the workbook**: the ASV table goes in as raw, the curated taxa as final, and ENA's run
   report as the library table.
6. **Check** with FAIRe-fier, then **Convert** to each destination.

## What to look for

- The raw tables (otuRaw, taxaRaw) and the final tables (otuFinal, taxaFinal): what changed in
  curation?
- experimentRunMetadata: each library's files, checksums and accessions, from ENA's run report.
- The negative controls: where are they described, and which conversions leave them out?
- Compare the Darwin Core archives from edna2obis (read counts) and FAIRe to Darwin Core (presence
  only).
