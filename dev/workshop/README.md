# Workshop materials: making FAIR eDNA datasets with the FAIRe tools app

These pages are draft material for a hands-on workshop with the FAIRe tools Shiny app. Each takes
participants through one demonstration dataset, from the published files to a checked FAIRe workbook
and the files for a repository. They are a starting point for discussion and will change.

| Page | Dataset | What it shows |
|---|---|---|
| [Khapra beetle](sheets/khapra.md) | qPCR of dust and air from two Canberra stores (Trujillo-González et al. 2022) | The least a targeted (qPCR) study needs; presence and absence records for GBIF; locations the authors withheld |
| [Nova Scotia eelgrass](sheets/eelgrass.md) | COI metabarcoding of invertebrates at 17 sites (Trask et al., Dryad) | What can be made FAIR from sparse published files, with details from the authors' code and the authors; what is lost without sequences |
| [SEA-MES](sheets/seames.md) | 16S fish metabarcoding of 13 water samples from RV Investigator (Deagle et al. 2025) | A full dataset: every sheet of the workbook and every conversion (NCBI, ENA, GBIF, OBIS, QIIME 2) |

Each page gives a short account of the study, how to install the app, the exercise step by step,
questions to discuss, and how to make the prepared files from the published ones.

## Running a session

- Send participants the install line on the page beforehand, as the first install takes about 15
  minutes.
- In the session, participants choose the dataset on the app's Start page and press *Load the
  demonstration data*: the app loads the files itself, so there is nothing to download. The page
  links to the files for anyone who wants to look at them or try the preparation.
- The khapra beetle page suits a short introduction, and SEA-MES a longer session. Groups could also
  take different datasets and compare.

## Handouts

If a workshop wants a zip for each dataset, with the page and every file in one folder,
[`make_packages.py`](make_packages.py) makes them. From the repository's folder (in Windows
PowerShell, or any terminal):

```
python dev/workshop/make_packages.py OUTDIR
```

It needs only Python. The app's own Python will do: `shiny\.venv\Scripts\python.exe` on Windows,
`shiny/.venv/bin/python` elsewhere.
