# FAIRe-Galaxy - making it easy to share your eDNA data

Environmental DNA (eDNA) data are most valuable when other people can find, understand and reuse
them. The FAIR eDNA (FAIRe) metadata standard describes how to record an eDNA study so that its
data are Findable, Accessible, Interoperable and Reusable, and the eDNA community has written a set
of tools for creating FAIRe metadata and sharing it with the places where data are kept.

This project brings those tools together so researchers can use them without writing code, in three
ways: in Galaxy, a free platform for data analysis that runs in a web browser; in an app on their own
computer; or in a chat with an AI assistant. The Galaxy tools are built for the Galaxy Australia eDNA
Lab, in collaboration with Galaxy Australia and Bioplatforms Australia.

With the tools you can:

- **make** a FAIRe metadata workbook, from a blank template or from the sample table, OTU tables and
  methods you already have;
- **check** the workbook against the FAIRe checklist;
- **convert** it for a sequence archive (NCBI or ENA), a biodiversity database (GBIF or OBIS), or an
  analysis in QIIME 2.

<details>
<summary><b>Want to understand where building shareable datasets fits into the eDNA workflow?</b></summary>

<br>

<img src="docs/images/faire_workflow_overview.png" alt="Flow chart in three panels. Before: data generation and bioinformatics produce the field, lab and analysis files you bring to FAIRe. FAIRe, run in Galaxy, the Shiny app or an AI assistant: start a FAIRe template, map your columns, validate, then convert the checked FAIRe workbook. A template-first route takes a blank template back to field and lab work and returns the filled template straight to validation. After: the workbook is converted for DNA data repositories (NCBI SRA, ENA) and biodiversity data repositories (GBIF, OBIS), where the data can be reused.">

</details>

## Three ways to use the tools

The same tools run in three places. Choose the one that suits you, and select its card or its link
under *Start here* to get going:

<p align="center">
<a href="#start-with-galaxy"><img src="docs/images/way_galaxy.svg" width="250" alt="Galaxy, in your web browser: nothing to install, a record of every step, joins your analysis workflows. Galaxy Australia eDNA Lab. Select to start with Galaxy."></a>
<a href="#start-with-the-shiny-app"><img src="docs/images/way_shiny.svg" width="250" alt="Shiny app, on your own computer: data stay with you, works offline, good for a first try. Needs R and Python. Select to start with the Shiny app."></a>
<a href="skill/README.md#setting-it-up"><img src="docs/images/way_ai.svg" width="250" alt="AI assistant, in a chat with Claude, ChatGPT or Microsoft 365 Copilot: talks you through each decision, copes with untidy files. Your files go to the AI company. Select to set up the AI assistant."></a>
</p>

| | Where it runs | Choose it if | Start here |
|---|---|---|---|
| 🟦 **Galaxy** | In your web browser, on Galaxy Australia's servers | you want nothing to install, a record of every step, or to join the FAIRe steps to your analysis workflows | [Start with Galaxy](#start-with-galaxy), below |
| 🟩 **Shiny app** | On your own computer; needs R and Python | your data must stay with you, you want to work offline, or you'd like a first try | [Start with the Shiny app](#start-with-the-shiny-app), below |
| 🟧 **AI assistant** | In a chat with Claude, ChatGPT or Microsoft 365 Copilot; your files go to the AI company | you'd like to be talked through each decision, or your files are untidy or unusual | [Setting up the AI assistant](skill/README.md#setting-it-up), in the skill's README |

All three use the same review sheets, so you can start in one and finish in another.

### Start with Galaxy

The tools will be in the [Galaxy Australia eDNA Lab](https://edna.dev.gvl.org.au), which is being
set up. Once they are there, open the Lab in your web browser and follow
[the guide to the tools](docs/faire_tools_guide.md). It says which tool to start with, depending on
what you already have, and the same guide is in each tool's help. Until then, the Shiny app and the
AI assistant run the same tools.

### Start with the Shiny app

With R (4.1 or later) and Python (3.10 to 3.13) on your computer, run this line in R. It downloads
the app, sets it up and opens it in your web browser:

```r
source("https://raw.githubusercontent.com/FAIR-eDNA/FAIRe-Galaxy/main/shiny/start.R")
```

Use this line each time you start the app: it checks for a newer version and updates itself.
Starting the app another way (*Run App* in RStudio, or `run_app.R`) uses the copy you have, though its
*Start* page tells you when a newer version is out.

The first time takes about 15 minutes, most of it downloading packages. To try the app before using
your own data, load one of the demonstration datasets on its *Start* page. The app's README has
[more on setting it up](shiny/README.md#downloading-and-running-it), including what to do if you
don't have Python yet, and [the demonstration datasets](shiny/README.md#trying-it-with-the-demonstration-data).

## The tools

The Galaxy tools wrap the community's scripts, and add a FAIRe mapper that turns a lab's own tables
into a FAIRe workbook. The Galaxy eDNA Lab is at edna.dev.gvl.org.au. The table lists them in the
order you would use them: make a workbook, check it, then convert it for where your data are going.

| Directory | Tools | What it does | Upstream | Status |
|---|---|---|---|---|
| `tools/faireator` | FAIRe-ator | **Make.** Makes a blank FAIRe metadata workbook, an Excel template set up for your study's assays and sample types, ready to fill in. | [FAIR-eDNA/FAIRe-ator](https://github.com/FAIR-eDNA/FAIRe-ator) | Lint clean; 3/3 tests pass; CC BY 4.0 licence copied in (`LICENSE.upstream`); templates open cleanly in Excel, LibreOffice and Google Sheets |
| `tools/faire_mapper` | FAIRe mapper: identify your files; profile columns; propose mapping; find primers; find method details; build primer table; apply mapping; ask a language model (optional) | **Make.** Builds a FAIRe workbook from the tables you already have. It works out what each file is, proposes which FAIRe term each column of your sample table matches (for you to review), finds the primers and other method details in your methods text, and writes the workbook. | New code, from the project's `faire_mapper` prototype; bundled primer table from Takahashi et al. 2023 and a bacteria and archaea register | Lint clean; 85/85 tests pass (Galaxy 26.1); benchmarked, tried on four Dryad datasets, two Australian datasets, the SEA-MES record (16S, COI, 18S and Wilderlab), the day-night study of West et al. 2024 (16S and COI, `dev/faire_mapper_daynight/`) and nine FAIRe examples; model step not yet run against the API |
| `tools/fairefier` | FAIRe-fier (with a new command-line version) | **Check.** Checks a FAIRe workbook against the FAIRe checklist and reports values that are missing or not in the expected form, so you can fix them before sharing. | [csiro/FAIRe-fier](https://github.com/csiro/FAIRe-fier) | Lint clean; 6/6 tests pass; outputs identical to the web app; offer the command line upstream |
| `tools/faire2ena` | FAIRe2ENA: samples; FAIRe2ENA: experiments and runs | **Convert.** Turns the workbook into the files the European Nucleotide Archive (ENA) needs to register your samples, study, experiments and sequencing runs. | [FAIR-eDNA/FAIRe2ENA](https://github.com/FAIR-eDNA/FAIRe2ENA) | Lint clean; 13/13 tests pass; runs can be chosen by assay or sequencing run, and a library holding several assays gets one run; adds the units ENA's checklist asks for, and the size-fraction fields the right way round; paired-end and single-end runs; ENA's test server accepted samples, study, experiments and runs for three SEA-MES 18S samples |
| `tools/faire2ncbi` | FAIRe2NCBI: BioSample; FAIRe2NCBI: SRA | **Convert.** Turns the workbook into the tables the NCBI Submission Portal needs to register your samples (BioSample) and sequence reads (SRA). | [aomlomics/FAIRe2NCBI](https://github.com/aomlomics/FAIRe2NCBI) | Lint clean; 20/20 tests pass; a library holding several assays gets one SRA row; needs a trial in the NCBI Submission Portal |
| `tools/faire2qiime` | FAIRe2QIIME | **Convert.** Turns the workbook into QIIME 2 sample metadata and, if you like, manifests for importing your reads, ready for analysis in QIIME 2. | [aomlomics/faire2qiime](https://github.com/aomlomics/faire2qiime) | Lint clean; 8/8 tests pass; needs a trial importing its files into QIIME 2 |
| `tools/faire2mdt` | FAIRe2MDT | **Convert.** Turns the workbook and an OTU table into the spreadsheet taken by GBIF's Metabarcoding Data Toolkit, which publishes eDNA records to GBIF. | [FAIR-eDNA/FAIRe2MDT](https://github.com/FAIR-eDNA/FAIRe2MDT) | Lint clean; 6/6 tests pass; leaves out control samples, as GBIF asks; ran on 11 assay and run combinations of the FAIRe examples; MDT trial reached an archive GBIF can index; CC BY 4.0 licence copied in (`LICENSE.upstream`) |
| `tools/edna2obis` | edna2obis: match taxa; edna2obis: build Darwin Core tables | **Convert.** Matches your taxa to accepted names in WoRMS and GBIF, then builds the Darwin Core tables OBIS and GBIF use to publish species occurrence records. | [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) | Lint clean; 14/14 tests pass (Galaxy 26.1, with internet access); one request at a time to WoRMS and GBIF by default, at most 4; needs a trial on Galaxy Australia and an IPT |
| `tools/faire2dwc` | FAIRe to Darwin Core | **Convert.** Turns the workbook into a Darwin Core archive of presence and absence records for GBIF and OBIS: qPCR and ddPCR results, or metabarcoding data published as presence. | New code (no upstream tool publishes qPCR results) | Lint clean; 5/5 tests pass (Galaxy 26.1); 162 records from the khapra beetle data (`demo/khapra`) and 1,046 with sequences from the eelgrass data; needs a trial in an IPT |

Each tool directory has its own README with what the wrapper adds, upstream issues found, and the
steps still needed before deployment.

## How to cite

If you use these tools, please cite three things:

- **This collection**: Berry O, Takahashi M, Bayer P, Coclet C, Formel S, Silliman K, Thompson LR,
  Willms B, Yong SY, Jeppesen TS, Frøslev TG (2026). FAIRe-Galaxy: tools for making, checking and
  sharing FAIR eDNA (FAIRe) datasets. https://github.com/FAIR-eDNA/FAIRe-Galaxy
- **The FAIRe checklist paper**: Takahashi M, Frøslev TG, Paupério J, et al. (2025). A metadata
  checklist and data formatting guidelines to make eDNA FAIR (Findable, Accessible, Interoperable,
  and Reusable). *Environmental DNA* 7(3): e70100. https://doi.org/10.1002/edn3.70100
- **The tools you ran**, as their authors ask: FAIRe-fier (Yong 2026,
  http://hdl.handle.net/102.100.100/734538), edna2obis (Willms and Silliman 2026,
  https://doi.org/10.5281/zenodo.23667395), and the repositories of FAIRe-ator, FAIRe2MDT,
  FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME, all listed in `CITATION.cff`. Galaxy shows each tool's
  citations on its page.

GitHub's *Cite this repository* button, on the right of the repository's front page, gives the
citation in other formats.

The collection's authors are the people who wrote the tools it brings together:

- Oliver Berry (CSIRO): the Galaxy wrappers, the FAIRe mapper, FAIRe to Darwin Core, the Shiny app
  and the AI assistant skill;
- Miwa Takahashi (CSIRO): FAIRe-ator (with Stephen Formel, The Data Patch) and FAIRe2MDT;
  she leads the FAIRe checklist and maintains these tools with Oliver Berry;
- Suk Yee Yong (CSIRO): FAIRe-fier;
- Philipp Bayer (Minderoo OceanOmics Centre at UWA): FAIRe2ENA;
- Clement Coclet, Luke Thompson, Katherine Silliman and Bayden Willms (NOAA 'Omics, AOML):
  FAIRe2NCBI, FAIRe2QIIME and edna2obis.

## Use of AI

Much of the new code and documentation in this repository (the Galaxy wrappers, the FAIRe mapper,
FAIRe to Darwin Core, the Shiny app and the AI assistant skill) was written with Claude, an AI model
made by Anthropic. Oliver Berry directed the work, reviewed the changes and tested the tools on
benchmark tables, published datasets and the demonstration sets in `demo/`, and the authors take
responsibility for the content. Claude is not listed as an author, as AI tools cannot take
responsibility for their work. The upstream tools wrapped here (FAIRe-ator, FAIRe-fier, FAIRe2MDT,
FAIRe2ENA, FAIRe2NCBI, FAIRe2QIIME and edna2obis) are their authors' own work.

The tools themselves do not use AI, with two exceptions that the user chooses: the optional *ask a
language model* step of the FAIRe mapper, and the AI assistant skill in `skill/`. Both send data to
the AI service the user picks, and say so before they do.

## Evaluating the tools

Notes for Galaxy Australia and other evaluators.

- **Where to start.** The table above lists the tools. Each tool folder's README says what the
  wrapper adds, what was tested and what is still to do. `docs/faire_tools_guide.md` is the guide
  shown at the end of every tool's help: where to start, the steps in order, and which tool serves
  which repository.
- **Installing.** Each folder under `tools/` is one ToolShed repository with its own tests
  (`planemo test tools/FOLDER`). The tools are not on the ToolShed yet. They will be published under
  the ToolShed account `fair-edna`, which is still to be registered. Dependencies come from conda
  (conda-forge and bioconda) or containers. All 160 tool
  tests pass on Galaxy release_26.1 in this repository's checks; the tools were also tested on
  release_25.0. Tools use profile 23.0, except *FAIRe mapper: ask a language model* (25.1, for
  Galaxy's credentials).
- **Data to try.** Each tool's `test-data/` folder (all under 200 KB). For a fuller example,
  `demo/seames` is a small copy of CSIRO's SEA-MES eDNA data record (CC BY 4.0), with the same
  files and layouts: sample sheets, 16S, 18S and Wilderlab ASV tables, methods text and ENA's run
  report. `DATA=demo/seames dev/faire_mapper_seames/run.sh OUTDIR` runs the FAIRe mapper, FAIRe-fier,
  FAIRe2NCBI, FAIRe2ENA, FAIRe2QIIME and (with R) FAIRe2MDT on it in about a minute. The three
  workflows in `workflows/faire/` chain the tools, each with its own tests.
- **A second worked dataset.** `demo/daynight` is a small copy of the day-night study of West et al.
  2024 (two assays, 120 samples and their controls; CC BY-NC 4.0, as its README says), in the
  authors' own formats: an eDNAFlow LCA output and a FASTA file per assay, a sample sheet with the
  time in its own column, and the portal's list of the fastq files. `DATA=demo/daynight dev/faire_mapper_daynight/run.sh OUTDIR` runs the FAIRe
  mapper, FAIRe-fier, FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME on it.
- **A targeted (qPCR) dataset.** `demo/khapra` holds the published files of a khapra beetle eDNA
  study (Trujillo-González et al. 2022, CC0): a sample table, 766 qPCR reactions and the Dryad
  README. `dev/faire_mapper_khapra/run.sh OUTDIR` runs the FAIRe mapper (with the qPCR results as
  ampData), FAIRe-fier and FAIRe to Darwin Core, to an archive of 162 presence and absence records
  for GBIF.
- **A minimal metabarcoding dataset.** `demo/eelgrass` holds the published files of a COI study of
  invertebrates in Nova Scotia eelgrass meadows (Trask et al., Dryad, CC0): reads per species and
  sample, and the site coordinates, with no sample table, controls or sequences.
  `dev/faire_mapper_eelgrass/run.sh OUTDIR` makes the sample table, then runs the FAIRe mapper,
  FAIRe-fier and FAIRe to Darwin Core, to 869 presence records for GBIF.
  `dev/faire_mapper_eelgrass/run_asvs.sh OUTDIR` adds the authors' per-ASV files from their GitHub
  repository (downloaded at run time): 1,046 records, each with the sequence behind it, and the
  controls.
- **Worked example.** `docs/walkthroughs/seames_18s_to_ena.md` follows three SEA-MES 18S samples
  from the lab's spreadsheet, through the FAIRe mapper, FAIRe-fier and FAIRe2ENA, to a submission
  that ENA's test service accepted. It ran the scripts the Galaxy tools wrap from the command line,
  so it shows the steps and their outputs, not Galaxy itself.
- **Without Galaxy.** `shiny/` is a Shiny app that runs the same tools on a person's own computer, in
  a web browser, with the same command lines (`shiny/README.md`). Its review screen is the FAIRe
  mapper's review sheet, and it can take a review sheet filled in with Excel. Its Start page offers
  demonstrations to load: SEA-MES (16S metabarcoding, the full dataset), the khapra beetle (qPCR) and
  Nova Scotia eelgrass (COI metabarcoding, the least a dataset needs), the last two to presence and
  absence records for GBIF.
- **Network.** Only *edna2obis: match taxa* needs the internet, to look up names in WoRMS and GBIF.
  It sends one request at a time by default, and at most 4.
- **Language model (optional).** *FAIRe mapper: ask a language model* needs a model service: one
  the server provides (set in the job rules) or the user's own key (Galaxy's credentials). Every
  other tool, and every other mapper step, works without one. It has not yet been run against a
  real model.
- **No submission.** No tool submits anything to NCBI, ENA, GBIF or OBIS, and none takes
  credentials. The tools write the files that users then submit themselves.
- **Job size.** The test jobs are small. edna2obis and FAIRe2MDT have not yet been timed on large
  OTU tables (thousands of sequences by hundreds of samples), which job rules may need.
- **Still to do.** A test-server trial of FAIRe2ENA's single-end runs (for Wilderlab data), a trial submission in NCBI's
  Submission Portal, importing FAIRe2QIIME's files into QIIME 2, and
  loading edna2obis's output into an IPT. Each
  tool's README lists its remaining steps.

## Layout

```
tools/
  faireator/      one ToolShed repository (bundles the FAIRe checklist v1.0.2)
  fairefier/      one ToolShed repository (command-line FAIRe-fier; checklists v1.0 and v1.0.2)
  faire2ena/      one ToolShed repository (two tools sharing macros.xml)
  faire2ncbi/     one ToolShed repository (two tools sharing macros.xml)
  faire2qiime/    one ToolShed repository
  faire2mdt/      one ToolShed repository
  edna2obis/      one ToolShed repository (two tools sharing macros.xml)
  faire2dwc/      one ToolShed repository (new: presence and absence records for GBIF and OBIS)
  faire_mapper/   one ToolShed repository (eight tools sharing macros.xml; bundles the checklist v1.0.2, its full template and a primer table)
workflows/faire/  three Galaxy workflows that chain the tools, each with its tests and test data
shiny/            a Shiny app that runs the tools on a person's own computer, without Galaxy
.github/workflows/pr.yaml   lint and tests on every change, adapted from the IUC's
.flake8           the IUC's flake8 settings; upstream scripts left out
```

**Workflows** (`workflows/faire/`, in the IWC layout: the `.ga` file to import, its source in
Galaxy's YAML format, `-tests.yml` and `test-data/`):

1. *FAIRe mapper: propose a mapping*: profile, propose mapping and find primers, from a lab's
   sample table and methods text.
2. *FAIRe mapper: write and check a FAIRe workbook*: apply mapping on the reviewed crosswalk, with
   an OTU table and values for the whole project, then FAIRe-fier.
3. *FAIRe: check a workbook and make submission tables*: FAIRe-fier, FAIRe2NCBI BioSample and SRA,
   FAIRe2ENA samples and FAIRe2QIIME from one workbook.

The steps name the tools by their bare IDs (`faire_mapper_apply`), as on a Galaxy with the tool
folders installed locally; once the tools are on the ToolShed, the IDs become ToolShed IDs.

**Continuous integration** (`.github/workflows/pr.yaml`) is the IUC's workflow with Galaxy
release_26.1 (as the IUC uses; current planemo cannot set up release_25.0 there), a manual trigger
that tests every tool, `dev/` ignored, no R lint, and the ToolShed deploy off until the repository variable
`TOOLSHED_DEPLOY` is `true` (after the owners in each `.shed.yml` and the secrets `TTS_API_KEY` and
`TS_API_KEY` are set). The owner in each `.shed.yml` is `fair-edna`.

`dev/` holds work that is not published to the ToolShed: `fairefier_equivalence/` checks that the
FAIRe-fier command line gives the same outputs as the web app; `faire_mapper_benchmark/` scores the
mapper on tables with known answers; `faire_mapper_real_datasets/` and
`faire_mapper_australian_datasets/` are the trials on four published Dryad eDNA datasets and two
Australian studies; `faire_mapper_seames/` runs every tool it can on CSIRO's SEA-MES eDNA data
(Deagle et al. 2025), from the published sample sheets to the NCBI and ENA run tables (its four
largest files are downloaded from the record, not stored here), and
`demo/seames` holds a demonstration set cut from it (25 samples, 0.5 MB, same files and layouts); `faire2mdt/` compares the FAIRe2MDT wrapper with the script run by hand on
the FAIRe examples; `faire_guide/` holds the shared help guide (below).

Every tool's help ends with the same guide, **Using the FAIRe tools in Galaxy**: where to start,
the steps in order, what each tool needs, and which tool serves which repository. It is the token
`@HELP_FAIRE_GUIDE@` in `faire_guide.xml`, one copy in each tool folder because each folder is its
own ToolShed repository. Edit `dev/faire_guide/faire_guide.xml` and run
`python dev/faire_guide/sync.py` to copy it into every folder (`--check` reports stale copies).
`docs/faire_tools_guide.md` has the same text in Markdown, for the Galaxy eDNA Lab pages.

Each directory is a self-contained ToolShed repository with its own `.shed.yml`, test data and the
upstream scripts copied unchanged. Small Galaxy-specific scripts (`faire2ena_galaxy.py`,
`faire2ncbi_galaxy.py`, `normalise_faire.py`, `faire2mdt_galaxy.R`, `edna2obis_galaxy.py`), the R
call written by `faireator.xml` and the FAIRe-fier command line (`fairefier_cli.py`) run before or
around the upstream code. The upstream files are not edited. The FAIRe2MDT and edna2obis drivers
replace functions inside the upstream code while it runs; their READMEs say which and why.

## Decisions

- **Standard FAIRe layout** (3 November 2026). Tools should read and write the FAIRe layout that
  FAIRe-ator produces (assay-specific projectMetadata columns headed `assay1`, `assay2` ..., or
  `project_level` for a single assay). Tools written for the FAIRe-NOAA layout are adapted to it,
  as the FAIRe2QIIME wrapper does, and their authors are asked to accept it. The FAIRe mapper's
  apply mapping tool writes this layout.
- **Licence** (3 November 2026). The wrapper code and the new code (the FAIRe mapper, the
  Galaxy drivers) are MIT, the usual licence for Galaxy tools (the IUC's tools-iuc repository is
  MIT). Each tool folder has the MIT `LICENSE`, and every `<tool>` element says `license="MIT"`,
  which Galaxy defines as the licence of the wrapper. Upstream scripts keep their own licences in
  `LICENSE.upstream`; `fairefier_cli.py`, derived from FAIRe-fier's code, keeps its BSD 3-Clause
  licence. The repository's own `LICENSE` (MIT, added by Miwa Takahashi on 11 November 2026) names
  CSIRO; the `LICENSE` in each tool folder and the workflows' creator still read "FAIRe Galaxy
  project contributors".
- **Upstream licences** (as given by the authors, 4 and 6 November 2026; the FAIRe-ator, FAIRe
  checklist and FAIRe2MDT licence files were added on 11 November 2026):

  | Upstream | Licence | Licence file in the repository |
  |---|---|---|
  | FAIRe-ator | CC BY 4.0 | Yes |
  | FAIReSheets (not wrapped) | MIT | Yes (added 9 November 2026) |
  | FAIRe-fier | BSD 3-Clause | Yes |
  | FAIRe2MDT | CC BY 4.0 | Yes |
  | edna2obis | MIT | Yes |
  | FAIRe2NCBI | CC0 1.0 | Yes |
  | FAIRe2ENA | MIT | Yes |
  | FAIRe2QIIME | CC0 1.0 | Yes |
  | FAIRe checklist (bundled with FAIRe-ator, FAIRe-fier and the FAIRe mapper) | CC BY 4.0 | Yes |

  `LICENSE.upstream` is copied in once each repository carries its licence file, and the FAIRe
  checklist's licence is in `checklist/LICENSE` in each folder that bundles it. FAIRe2MDT was
  first given as CC BY-SA 4.0; its licence file, added on 11 November 2026, is CC BY 4.0.
- **Primer table** (3 November 2026). The Takahashi et al. 2023 primer tables and the Wilderlab
  assay list are confirmed for inclusion with the FAIRe mapper tools.
- **GitHub home** (3 and 11 November 2026). The repository is
  [FAIR-eDNA/FAIRe-Galaxy](https://github.com/FAIR-eDNA/FAIRe-Galaxy). Galaxy Australia advises
  that the tools go to the IUC, or stay with maintainers who publish them from their own ToolShed
  account. Galaxy Australia does not want to manage the tools, as it lacks the domain knowledge.
- **ToolShed owner and maintainers** (23 November 2026). The tools are published under a FAIR-eDNA
  account on the ToolShed, `fair-edna`, and maintained by Oliver Berry and Miwa Takahashi (CSIRO),
  with the FAIRe committee that Miwa chairs. The FAIRe team looks after the checklist and several of
  the upstream scripts, so it holds the knowledge the tools need. Maintenance happens in this
  repository: a change merged to `main` is published to the ToolShed by the continuous
  integration. Galaxy Australia installs the tools on the eDNA Lab and updates them when the
  maintainers ask. On 24 November 2026 Oliver Berry and Miwa Takahashi agreed to be the custodians
  of the account. `fair-edna` is registered with Oliver Berry's CSIRO email, and Miwa Takahashi has
  her own ToolShed account, registered with her CSIRO email, with write access to every
  repository.
- **Language model optional.** Every tool works without one. A model's answers are marked as
  such, and only a person's answers count as confirmed.
- **Credit and ownership** (7 November 2026). Oliver Berry (CSIRO) wrote the Galaxy tools for the
  upstream FAIRe tools and developed the FAIRe mapper, with Claude (Anthropic). Each tool's help
  credits both, and its `<creator>` block names him and Miwa Takahashi, the maintainers (see
  ToolShed owner and maintainers above). Each upstream tool stays with its own developers.

## Steps common to all tools

`docs/faire_tools_guide.md`
(the guide to all the tools) and `docs/faire_mapper_inputs.md` (the guide to the FAIRe mapper's
inputs) are the texts the tools show in Galaxy, for reuse on the Galaxy eDNA Lab pages.
`docs/ena_submission_from_galaxy.md` looks at the IUC's ENA Upload tool as a way to submit FAIRe
data to ENA from inside Galaxy.

1. Agree with the upstream authors that the wrappers can be published, and report the issues listed
   in each README, and ask for tagged releases. The issues for edna2obis, FAIRe2QIIME and FAIRe2NCBI
   were posted on 17 November 2026; the others are still to report. (All the upstream repositories
   now have licence files: FAIRe-ator, the FAIRe checklist and FAIRe2MDT added theirs on 11
   November 2026.)
2. ToolShed owner `fair-edna` (decided 23 November 2026; filled in each `.shed.yml`, with Oliver
   Berry and Miwa Takahashi in each `<creator>` block; custodians and emails agreed 24 November
   2026). Still to do: register `fair-edna` on the main ToolShed and the Test ToolShed with Oliver
   Berry's CSIRO email; add their API keys as the repository secrets `TS_API_KEY` and
   `TTS_API_KEY`; set the repository variable `TOOLSHED_DEPLOY` to `true`; and, once the
   repositories exist, give Miwa Takahashi's ToolShed account write access to each one.
3. Continuous integration (done, `.github/workflows/pr.yaml`). The IUC's planemo-ci GitHub Actions workflow runs lint and tests on
   every pull request and can publish to the ToolShed on merge.
4. Publish to the Test ToolShed, check the tools install on a test Galaxy, then publish to the main
   ToolShed.
5. Ask the Galaxy Australia team to install the tools in the eDNA lab, in a section such as
   *eDNA data submission*.
6. Longer term: bioconda packages for the upstream code (or one consolidated FAIRe package), so the
   wrappers no longer bundle scripts.

## Running the checks

```bash
pip install planemo
cd tools
planemo lint faireator fairefier faire2ena faire2ncbi faire2qiime faire2mdt edna2obis faire_mapper
planemo test faireator fairefier faire2ena faire2ncbi faire2qiime faire2mdt edna2obis faire_mapper
```

`planemo test` downloads Galaxy and builds conda environments (R for FAIRe-ator and FAIRe2MDT;
python, pandas and openpyxl, plus pydantic for FAIRe-fier, pyyaml for FAIRe2NCBI, and pyworms and
pygbif for edna2obis) on the first run, which takes a while. Galaxy will not start as root, so run
the tests as an ordinary user.

On 11 November 2026, this repository's GitHub checks passed all 115 tool tests in the eight tool
folders (Galaxy `release_26.1`, tools in containers, with internet access). The earlier history
follows.

Tests were run together on 4 November 2026, after the shared guide was added, with planemo
0.75.47 against Galaxy `release_25.0`, for all eight tool folders (15 tools) in one Galaxy: 69 of 71
passed. The 2 that did not are edna2obis's taxon-matching tests, which need WoRMS and GBIF; this
workspace cannot reach them, and both stopped with the tool's own message, as they should. Give the
tool folders to `planemo test` one by one (as above): given only `tools/`, planemo does not look
inside the folders.

| Tool folder | Tests passed |
|---|---|
| faireator | 3 of 3 |
| fairefier | 6 of 6 |
| faire2ena | 6 of 6 |
| faire2ncbi | 14 of 14 |
| faire2qiime | 4 of 4 |
| faire2mdt | 4 of 4 |
| edna2obis | 11 of 11 on GitHub with internet access; 9 of 11 here (the 2 match tests need WoRMS and GBIF) |
| faire_mapper | 13 of 13 |

After that run, the FAIRe mapper's apply mapping tool and its 8 tests, and 2 tests for the data
dictionary in propose mapping, were added (version 0.4.0); the faire_mapper folder was then tested on
its own: 23 of 23 passed. On 4 November, after the fixes from the SEA-MES trial (mapper 0.5.0 and
the FAIRe2NCBI wrapper), the faire_mapper and faire2ncbi folders were tested again: 26 of 26 and 15
of 15 passed. Later that day, with PR2 and SILVA lineages, primer sequences in methods text, and raw
and final OTU tables for one assay, the faire_mapper folder passed 30 of 30. On 5 November all eight
folders were tested again in one run, after the flake8 fixes, the FAIRe2ENA run filter and the
mapper's new inputs: 81 of 83 passed, and the other 2 are edna2obis's taxon-matching tests, which
need WoRMS and GBIF and stop with the wrapper's message about internet access. The three workflows
passed their tests in the same Galaxy (`workflows/faire/README.md`).

On 6 November 2026 the repository's GitHub workflow ran every tool's tests, with internet access, on
Galaxy `release_26.1` with the tools in containers: 94 of 95 passed. The GBIF match test failed,
which showed two problems in edna2obis (pygbif 0.6.6, and Excel output to a `.dat` path; see its
README). After the fixes all 11 edna2obis tests passed there, including both match tests.

Galaxy job scripts set `PYTHONWARNINGS=ignore`. Any tool that reports problems through Python's
warnings module needs to undo that (FAIRe-fier does); check this when wrapping the next tools.
