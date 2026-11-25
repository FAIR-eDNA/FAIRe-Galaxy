# Demonstration files

The datasets the app's Start page offers. Each folder holds the files a person would add, prepared as
the FAIRe mapper's guide describes, and a README with the source, the licence and the changes made.
`R/demos.R` holds each one's settings: the forms it fills in and the reviewer's decisions.

| Folder | Dataset | What it shows | Licence |
|---|---|---|---|
| `seames` | SEA-MES eDNA data record (Deagle et al. 2025), 13 water samples, 16S fish | Metabarcoding with every part: sequences, raw and curated tables, run report, methods, controls; every conversion | CC BY 4.0 |
| `eelgrass` | Nova Scotia eelgrass COI metabarcoding (Trask et al., Dryad), 50 samples at 17 sites | Metabarcoding with the least it needs: reads per species and sample, and site coordinates; no sample table, controls or sequences; to GBIF as presence | CC0 1.0 |
| `khapra` | Khapra beetle qPCR (Trujillo-González et al. 2022), 90 samples and controls, 766 reactions | A targeted study with the least it needs: samples, assay details, a result for each reaction; to GBIF as presence and absence | CC0 1.0 |

The demonstrations load no values for the whole project. You find them in each dataset's files with
find primers and find method details, and type the rest, as you would with your own data. Where the
published files leave out a detail the workbook needs, a notes file in the folder gives it, with its
source.

**These files are for trying the tools, not for ecological analysis.** Use the published records for
that.

For a workshop, `dev/workshop/make_packages.py` makes a zip of each dataset, holding the published files
as downloaded, the same files prepared for the app, and a page of steps for participants.
