# Khapra beetle: a qPCR dataset to GBIF

Khapra beetle (*Trogoderma granarium*) is a serious pest of stored grain. In 2020, biosecurity
officers vacuumed dust and air from two Canberra stores that had sold infested goods. The samples
were tested with two qPCR assays, each on a benchtop and a portable machine (Trujillo-González et al.
2022). The authors published a sample table, a table of 766 qPCR reactions and a README on Dryad
(CC0).

This exercise turns those files into a FAIRe workbook, checks it, and makes a Darwin Core archive of
presence and absence records that could go to GBIF.

## What is in this folder

- `published/`: the three files as they are on Dryad.
- `prepared/`: the same files with the columns a person adds before mapping (see *Doing the
  preparation yourself*), plus the project values and a taxon table. The app's demonstration loads
  these.
- `README.md`: the source and licence.

[[COMMON]]

## The exercise

1. On the app's **Start** page, choose **Khapra beetle** and press *Load the demonstration data*.
   (Or add the files in `prepared/` yourself with *Add files*.)
2. **1. Make a workbook, FAIRe mapper, a. Your files**: run it. It should find a sample table, the
   qPCR results, the project values, a taxon table and the README.
3. **b. Propose a mapping**: run it on `khapra_samples_prepared.csv`, with the README as the data
   dictionary and *Targeted* as the assay type.
4. **c. Review the mapping**. Decide the rows for review, then save the review. Suggested answers:
   - Reject *sample type* (the authors' own categories, kept as their own column);
   - Change *Category* to samp_category;
   - Change *Extraction technique* to nucl_acid_ext_kit.

   *Fill in the authors' answers* does this for you.
5. **d. Methods and project values**: the project values are filled in. Look at what they hold for
   each assay: primers, probe, cycling conditions, limit of detection.
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
- The store locations were withheld. What do decimalLatitude, coordinateUncertaintyInMeters,
  informationWithheld and dataGeneralizations say?

## Doing the preparation yourself

To see what a person adds before mapping, start from `published/` and add these columns in Excel:

- to `Sample_metadata.csv`:
  - *Category*: sample, negative control or positive control, from *sample type*;
  - *Latitude*, *Longitude* and *coordinateUncertaintyInMeters*: the centre of Tuggeranong or
    Fyshwick, with an uncertainty that covers it;
  - *State*, and ENVO terms for env_broad_scale, env_local_scale and env_medium;
- to the qPCR results: an *assay_name* column naming each assay and machine (for example
  OlsonViiA7), with no underscores.

Then compare your files with those in `prepared/`.
