# Khapra beetle demonstration set

The published files of a qPCR study of khapra beetle (*Trogoderma granarium*) eDNA, for
demonstrating the FAIRe tools on a targeted assay. It is a small but complete dataset that can go
from the authors' two tables to a FAIRe workbook that passes FAIRe-fier and a Darwin Core archive
ready for GBIF. It shows the least a targeted study needs: samples with a place and a date, the assay
details, and a result for each reaction.

## Source and licence

Trujillo-González A, Thuo DN, Divi U, Sparks K, Wallenius T, Gleeson D (2022). Data from: Detection of
khapra beetle environmental DNA using portable technologies in Australian biosecurity. Dryad,
[doi:10.5061/dryad.jwstqjq96](https://doi.org/10.5061/dryad.jwstqjq96). Released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), as is all data on Dryad.

The paper: Trujillo-González A, Thuo DN, Divi U, Sparks K, Wallenius T, Gleeson D (2022). Detection
of khapra beetle environmental DNA using portable technologies in Australian biosecurity.
*Frontiers in Insect Science* 2: 795379,
[doi:10.3389/finsc.2022.795379](https://doi.org/10.3389/finsc.2022.795379), CC BY 4.0. It is not
included here; the project values in `dev/faire_mapper_khapra/project_values.tsv` come from it and
from the Dryad README. `khapra_notes.md` gives, in our words, the details of the assays from the
paper that the README leaves out, so that the Shiny app's demonstration can find them in its files.

The three files from Dryad are as published, with the names Dryad gives them.

## Files

| File | What it holds |
|---|---|
| `Sample_metadata.csv` | 90 rows: 57 dust and air samples, 9 field controls, 15 extractions of a positive dust sample and 9 tissue samples. Sample ID, location, sample type, collection method, extraction technique and date (day first) |
| `Amplification_data_khapra_05012022_dryad.csv` | 766 qPCR reactions: sample, location, Cq (or *Undetermined*), assay (Olson or Furui), collection method, extraction and machine (ViiA7 or Franklin) |
| `Trujillo_Gonzalez_et_al_2022_README.txt` | The Dryad README: authors, file descriptions, primers, probes and cycling conditions. Used as the data dictionary and for the method details |
| `khapra_notes.md` | Ours, not published: from the paper, where each assay comes from, its limit of detection, how a detection was called, why field controls amplified, and the licence |

## Running it

From the top of the repository:

```
bash dev/faire_mapper_khapra/run.sh OUTDIR
```

It runs each step as a person would in Galaxy or the Shiny app:

1. **Prepare the tables** (`prepare_table.py`, `prepare_results.py`). These add what a person
   following the mapper's guide adds before mapping, and leave the published files unchanged:
   - a *Category* column (sample, negative control or positive control) and the control types;
   - the state, so geo_loc_name reads *Australia: Australian Capital Territory, Tuggeranong*;
   - *Latitude* and *Longitude* as "missing: restricted access", as the authors withheld the
     stores' locations (see below);
   - ENVO terms: urban biome, shop, and dust or air;
   - for the results, an assay name for each assay and machine (OlsonViiA7, OlsonFranklin,
     FuruiViiA7 and FuruiFranklin), as FAIRe treats each combination as an assay with its own
     conditions.
2. **Propose mapping** on the sample table, with the Dryad README as its data dictionary, then the
   reviewer's decisions (`reviewer_decisions.tsv`, 3 rows).
3. **Find method details** in the README, to compare with the project values.
4. **Apply mapping**, with the qPCR results. This writes the reactions to ampData and works out
   detected_notDetected for each sample and assay. The project values (`project_values.tsv`) give
   the primers, probes, cycling conditions, limits of detection and the other assay details from the
   paper.
5. **FAIRe-fier** checks the workbook.
6. **FAIRe to Darwin Core** writes the archive for GBIF, with the higher taxonomy from
   `taxa_khapra.tsv`.

## What you should see

- FAIRe-fier: *Success* for projectMetadata and sampleMetadata. It warns only about the column kept
  as a user-defined field (sample_type).
- Apply mapping warns about one Cq of 0, 23 OlsonViiA7 reactions with a Cq above the assay's 50
  cycles and 49 FuruiViiA7 reactions above 45 (see below).
- FAIRe to Darwin Core writes 162 records, with the 33 controls left out. Its report notes that
  decimalLatitude is empty in every record, which GBIF recommends and OBIS requires:

  | Assay | Present | Absent | Not written |
  |---|---|---|---|
  | OlsonViiA7 | 17 | 35 | 5 |
  | OlsonFranklin | 4 | 25 | 28 |
  | FuruiViiA7 | 26 | 24 | 7 |
  | FuruiFranklin | 28 | 3 | 26 |

  *Not written* means the sample was not tested with that assay and machine. By place: Tuggeranong
  61 present and 84 absent; Fyshwick 14 present and 3 absent.

The archive is for demonstration. It has not been published to GBIF, as the data belong to the
authors.

## Things to know about these data

- **Locations were withheld.** The authors left out the stores' locations as sensitive, and the
  published files have no coordinates. The workbook gives decimalLatitude and decimalLongitude as
  "missing: restricted access", and only the district or suburb the authors name (Tuggeranong,
  Fyshwick) in geo_loc_name. informationWithheld says so and goes to GBIF with each record, whose
  locality is the district or suburb. No coordinates are made up from the place names: that would
  add a position the authors chose not to give.
- **Field negative controls amplified.** The paper reports positive replicates in field controls
  from both stores (8 of 65 at Tuggeranong, 6 of 12 at Fyshwick), and the Fyshwick samples were
  collected with a vacuum cleaner used in an earlier khapra beetle response. Some present records may
  come from contamination. The archive's abstract says so; a data user should read it before using
  the records.
- **How a sample counts as present.** A sample is present for an assay when at least one replicate
  amplified, as the paper's detection criteria describe. The replicate counts match the paper's
  Table 2, except for the Furui field-control replicates at Tuggeranong (30 here, 29 in the paper).
- **Cq values above the number of cycles.** No run can give a Cq above its number of cycles, so
  these values need checking with the authors. They are kept as published.
- **No sequences.** Some amplicons were confirmed by Sanger sequencing (GenBank MW911673 to
  MW911691), but the published files do not say which sample each came from, so the records carry
  the primers and probe, not a sequence.
- **Assay names without underscores.** FAIRe-fier takes an assay's name to be the text after the
  last underscore of `detected_notDetected_<assay_name>`, so names such as Olson_ViiA7 fail its
  check. This is listed with the upstream issues in `tools/faire_mapper/README.md`.
- **The LAMP assay** in the Dryad README failed on environmental samples and has no results in the
  data file.
