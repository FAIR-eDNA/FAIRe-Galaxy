# SEA-MES: a full metabarcoding dataset

Thirteen 10 L water samples (two of them field controls) from CSIRO's RV Investigator, from the
South-East Australian Marine Ecosystem Survey (Deagle et al. 2025, CSIRO Data Access Portal, CC BY
4.0). The files are a small cut of the published record. They hold:

- the sample sheet;
- a 16S fish ASV table with a sequence and preliminary taxonomy for each ASV;
- the authors' curated fish taxa;
- ENA's report of the sequencing runs;
- the methods.

This exercise fills every sheet of a FAIRe workbook and runs every conversion: NCBI, ENA, GBIF, OBIS
and QIIME 2.

## What is in this folder

- `files/`: the files the app's demonstration loads.
- `README.md`: the source, the licence and the changes made.

[[COMMON]]

## The exercise

1. On the app's **Start** page, choose **SEA-MES** and press *Load the demonstration data*.
2. **1. Make a workbook, FAIRe mapper**: run *a. Your files*, then *b. Propose a mapping* on
   `SEA-MES_10L_samples.csv`.
3. **c. Review the mapping**: decide the six rows for review, then save. Suggested answers:
   - Accept Control_Neg as samp_category, *depth, and samp_vol_we_dna_ext;
   - Reject replicate, bioproject_accession and Location.

   *Fill in the authors' answers* does this for you.
4. **d. Methods and project values**: find primers in `methods.txt`.
5. **e. Write the workbook**: the ASV table goes in as raw, the curated taxa as final, and ENA's run
   report as the library table.
6. **2. Check** with FAIRe-fier, then **3. Convert** to each destination.

## What to look for

- The raw tables (otuRaw, taxaRaw) and the final tables (otuFinal, taxaFinal): what changed in
  curation?
- experimentRunMetadata: each library's files, checksums and accessions, from ENA's run report.
- The negative controls: where are they described, and which conversions leave them out?
- Compare the Darwin Core archives from edna2obis (read counts) and FAIRe to Darwin Core (presence
  only).
