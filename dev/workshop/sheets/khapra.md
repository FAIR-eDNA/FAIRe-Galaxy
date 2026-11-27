# Khapra beetle: a qPCR dataset to GBIF

Khapra beetle (*Trogoderma granarium*) is a serious pest of stored grain. In 2020, biosecurity
officers vacuumed dust and air from two Canberra stores that had sold infested goods. The samples
were tested with two qPCR assays, each on a benchtop and a portable machine (Trujillo-González et al.
2022). The authors published a sample table, a table of 766 qPCR reactions and a README on Dryad
(CC0).

This exercise turns those files into a FAIRe workbook, checks it, and makes a Darwin Core archive of
presence and absence records that could go to GBIF.

## The files

You don't need to download anything for the exercise: the app loads the files itself. They are here
to look at, and for *Doing the preparation yourself* at the end. To download one, open it and press
*Download raw file* at the top right.

- As published on Dryad ([`demo/khapra`](../../../demo/khapra), with the source and licence in its
  README): [`Sample_metadata.csv`](../../../demo/khapra/Sample_metadata.csv),
  [`Amplification_data_khapra_05012022_dryad.csv`](../../../demo/khapra/Amplification_data_khapra_05012022_dryad.csv)
  and [`Trujillo_Gonzalez_et_al_2022_README.txt`](../../../demo/khapra/Trujillo_Gonzalez_et_al_2022_README.txt).
- Prepared for the app ([`shiny/demo/khapra`](../../../shiny/demo/khapra)): the same files with the columns
  a person adds before mapping ([`khapra_samples_prepared.csv`](../../../shiny/demo/khapra/khapra_samples_prepared.csv),
  [`khapra_qpcr_prepared.csv`](../../../shiny/demo/khapra/khapra_qpcr_prepared.csv)), a taxon table
  ([`khapra_taxa.tsv`](../../../shiny/demo/khapra/khapra_taxa.tsv)), and
  [`khapra_notes.md`](../../../shiny/demo/khapra/khapra_notes.md), the details of the assays from the paper
  that the README leaves out.

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

1. On the app's **Start** page, choose **Khapra beetle** and press *Load the demonstration data*.
   (Or download the prepared files and add them yourself with *Add files*.)
2. **1. Make a workbook, FAIRe mapper, a. Your files**: run it. It should find a sample table, the
   qPCR results, a taxon table, the README and the notes.
3. **b. Propose a mapping**: run it on `khapra_samples_prepared.csv`, with the README as the data
   dictionary and *Targeted* as the assay type.
4. **c. Review the mapping**. Decide the rows for review, then save the review. Suggested answers:
   - Reject *sample type* (the authors' own categories, kept as their own column);
   - Change *Category* to samp_category;
   - Change *Extraction technique* to nucl_acid_ext_kit.

   *Fill in the authors' answers* does this for you.
5. **d. Methods and project values**: the values for the whole project start empty, and each
   assay needs its own. Open *1. Find the primers*, run *Find primers* on the README and the notes, and add each pair for the
   two assays that used it (type *OlsonViiA7, OlsonFranklin*, then *FuruiViiA7, FuruiFranklin*).
   Go on to *2. Find the other method details* with *Targeted*: four values come ticked. Which of them
   belong in the sample table instead? Which cycling conditions belong to which machine? Which values
   are the LAMP assay's, and so not for these data? In step 3, add the rest by hand from the notes: the
   app lists the mandatory terms still to give, and the steps on the Start page give each value.
6. **e. Write the workbook**: the qPCR results are filled in. Write the workbook and read its
   warnings.
7. **2. Check**: run FAIRe-fier on the workbook.
8. **3. Convert, GBIF and OBIS (presence and absence)**: write the Darwin Core archive and read its
   report.

## What to look for

- The workbook has an ampData sheet with every reaction, and a detected_notDetected column for each
  of the four assays (each assay on each machine). Which samples were not tested with an assay?
- Apply mapping warns about Cq values above the number of cycles. How can that happen, and what
  would you ask the authors?
- The archive has 162 records: 75 present and 87 absent. The 33 controls are left out. Why does
  GBIF want the absences?
- The field negative controls amplified too. Where in the archive would a data user learn that?
- The store locations were withheld. What do decimalLatitude, geo_loc_name and
  informationWithheld say, and what does the archive's report say about the missing coordinates?

## Doing the preparation yourself

To see what a person adds before mapping, start from the published files and add these columns in
Excel:

- to `Sample_metadata.csv`:
  - *Category*: sample, negative control or positive control, from *sample type*;
  - *Latitude* and *Longitude*: "missing: restricted access" for the samples, as the authors
    withheld the stores' locations;
  - *State*, and ENVO terms for env_broad_scale, env_local_scale and env_medium;
- to the qPCR results: an *assay_name* column naming each assay and machine (for example
  OlsonViiA7), with no underscores.

Then compare your files with the prepared ones.
