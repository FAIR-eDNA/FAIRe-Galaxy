# Nova Scotia eelgrass demonstration

The files of a COI metabarcoding study of invertebrates in eelgrass meadows across Nova Scotia,
prepared for the app. They come from `demo/eelgrass` in this repository, which holds the published
files and describes the data and what to know about them. `dev/faire_mapper_eelgrass/make_app_demo.sh`
makes this folder from them. **They are not data for ecological analysis**; use the published record
for that.

| File | What it is |
|---|---|
| `eelgrass_samples_prepared.csv` | The sample table a person following the mapper's guide makes, as the study published none: one row per column of the species table (50 samples at 17 sites), with the site's coordinates, the period of sampling, the country and province, Category and ENVO terms (`dev/faire_mapper_eelgrass/prepare_table.py`) |
| `Final_ASVTable_withTaxonomy_Filtered.csv` | The published table of reads per species and sample (138 taxa), as published |
| `Dryad_README.md` | The Dryad README, as published: the data dictionary for propose mapping, and the methods |
| `eelgrass_project_values.tsv` | Values for the whole project and the assay: the primers, target gene, pipeline, reference database, sequencing platform and location, licence and citation (`dev/faire_mapper_eelgrass/project_values.tsv`) |
| `eelgrass_taxa.tsv` | The taxon table for FAIRe to Darwin Core: each name with kingdom Animalia and the authors' phylum and class (`dev/faire_mapper_eelgrass/make_taxa.py`) |

## Source and licence

Data from: Applying eDNA metabarcoding to assess invertebrate biodiversity of eelgrass (*Zostera
marina*) meadows across Nova Scotia (2025). Dryad,
[doi:10.5061/dryad.gqnk98t0c](https://doi.org/10.5061/dryad.gqnk98t0c). CC0 1.0. The changes made
are listed above and in `demo/eelgrass/README.md`.
