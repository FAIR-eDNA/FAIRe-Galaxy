# Khapra beetle demonstration

The files of a qPCR study of khapra beetle (*Trogoderma granarium*) eDNA, prepared for the app. They
come from `demo/khapra` in this repository, which holds the published files and describes the data
and what to know about them. `dev/faire_mapper_khapra/make_app_demo.sh` makes this folder from them.
**They are not data for ecological analysis**; use the published record for that.

| File | What it is |
|---|---|
| `khapra_samples_prepared.csv` | The published sample table (Sample_metadata.csv), with the columns a person following the mapper's guide adds: Category (sample, negative control or positive control), the control types, the state, coordinates for the samples and ENVO terms (`dev/faire_mapper_khapra/prepare_table.py`) |
| `khapra_qpcr_prepared.csv` | The published qPCR results (Amplification_data_khapra_05012022_dryad.csv), with an assay_name for each assay and machine (OlsonViiA7, OlsonFranklin, FuruiViiA7, FuruiFranklin) and pcr_plate_id (`dev/faire_mapper_khapra/prepare_results.py`) |
| `Trujillo_Gonzalez_et_al_2022_README.txt` | The Dryad README, as published: the data dictionary for propose mapping, and the methods |
| `khapra_project_values.tsv` | Values for the whole project and each assay, from the paper and the README: primers, probes, cycling conditions, limits of detection, the licence, and what was withheld (`dev/faire_mapper_khapra/project_values.tsv`) |
| `khapra_taxa.tsv` | The taxon table for FAIRe to Darwin Core: the name with its authority and higher taxonomy |

## Source and licence

Trujillo-González A, Thuo DN, Divi U, Sparks K, Wallenius T, Gleeson D (2022). Data from: Detection of
khapra beetle environmental DNA using portable technologies in Australian biosecurity. Dryad,
[doi:10.5061/dryad.jwstqjq96](https://doi.org/10.5061/dryad.jwstqjq96). CC0 1.0. The project
values draw on the paper: Trujillo-González et al. (2022), *Frontiers in Insect Science* 2: 795379,
[doi:10.3389/finsc.2022.795379](https://doi.org/10.3389/finsc.2022.795379), CC BY 4.0.

The changes made are listed above. The store locations were withheld by the authors, so the
coordinates are the centres of the district and suburb they name; see `demo/khapra/README.md`.
