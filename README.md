# FAIRe-Galaxy

Integrates FAIRe eDNA tools into Galaxy via reusable tool wrappers and workflows. Built for the Galaxy eDNA Lab in collaboration with Galaxy Australia and Bioplatforms Australia.

Galaxy tool wrappers for scripts that convert FAIR eDNA (FAIRe) metadata into formats needed for
analysis and for submission to global repositories, and a FAIRe mapper that turns a lab's own
tables into a FAIRe workbook. The Galaxy eDNA Lab is at edna.dev.gvl.org.au.

| Directory | Tools | Upstream | Status |
|---|---|---|---|
| `tools/faireator` | FAIRe-ator | [FAIR-eDNA/FAIRe-ator](https://github.com/FAIR-eDNA/FAIRe-ator) | Lint clean; 3/3 tests pass; CC BY 4.0 licence copied in (`LICENSE.upstream`); templates open cleanly in Excel, LibreOffice and Google Sheets |
| `tools/fairefier` | FAIRe-fier (with a new command-line version) | [csiro/FAIRe-fier](https://github.com/csiro/FAIRe-fier) | Lint clean; 6/6 tests pass; outputs identical to the web app; offer the command line upstream |
| `tools/faire2ena` | FAIRe2ENA: samples; FAIRe2ENA: experiments and runs | [FAIR-eDNA/FAIRe2ENA](https://github.com/FAIR-eDNA/FAIRe2ENA) | Lint clean; 10/10 tests pass; runs can be chosen by assay or sequencing run, and a library holding several assays gets one run; needs ENA test-server trial |
| `tools/faire2ncbi` | FAIRe2NCBI: BioSample; FAIRe2NCBI: SRA | [aomlomics/FAIRe2NCBI](https://github.com/aomlomics/FAIRe2NCBI) | Lint clean; 17/17 tests pass; a library holding several assays gets one SRA row; needs a trial in the NCBI Submission Portal |
| `tools/faire2qiime` | FAIRe2QIIME | [aomlomics/faire2qiime](https://github.com/aomlomics/faire2qiime) | Lint clean; 4/4 tests pass; needs trial with a FAIRe-ator workbook and QIIME 2 |
| `tools/faire2mdt` | FAIRe2MDT | [FAIR-eDNA/FAIRe2MDT](https://github.com/FAIR-eDNA/FAIRe2MDT) | Lint clean; 6/6 tests pass; leaves out control samples, as GBIF asks; ran on 11 assay and run combinations of the FAIRe examples; MDT trial reached an archive GBIF can index; CC BY 4.0 licence copied in (`LICENSE.upstream`) |
| `tools/edna2obis` | edna2obis: match taxa; edna2obis: build Darwin Core tables | [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) | Lint clean; all 11 tests pass on GitHub with internet access (Galaxy 26.1, 6 November 2026), and the 9 build tests also offline here; needs a trial on Galaxy Australia and an IPT |
| `tools/faire_mapper` | FAIRe mapper: identify your files (says what each file is and where it goes); profile columns; propose mapping; find primers; build primer table; apply mapping (writes a FAIRe workbook); ask a language model (optional answers for the columns to review) (plus a model script for methods text) | New code, from the project's `faire_mapper` prototype; bundled primer table from Takahashi et al. 2023 and a bacteria and archaea register | Lint clean; 49/49 tests pass (Galaxy 26.1); benchmarked, tried on four Dryad datasets, two Australian datasets, the SEA-MES record (16S, COI, 18S and Wilderlab) and nine FAIRe examples; model step not yet run against the API |

Each tool directory has its own README with what the wrapper adds, upstream issues found, and the
steps still needed before deployment.

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
  faire_mapper/   one ToolShed repository (seven tools sharing macros.xml; bundles the checklist v1.0.2, its full template and a primer table)
workflows/faire/  three Galaxy workflows that chain the tools, each with its tests and test data
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
`TS_API_KEY` are set). Its lint step fails on warnings, so the placeholder owners in `.shed.yml`
will fail it until they are filled in.

`dev/` holds work that is not published to the ToolShed: `fairefier_equivalence/` checks that the
FAIRe-fier command line gives the same outputs as the web app; `faire_mapper_benchmark/` scores the
mapper on tables with known answers; `faire_mapper_real_datasets/` and
`faire_mapper_australian_datasets/` are the trials on four published Dryad eDNA datasets and two
Australian studies; `faire_mapper_seames/` runs every tool it can on CSIRO's SEA-MES eDNA data
(Deagle et al. 2025), from the published sample sheets to the NCBI and ENA run tables (its four
largest files are downloaded from the record, not stored here), and
`demo/seames` holds a demonstration set cut from it (23 samples, 0.5 MB, same files and layouts); `faire2mdt/` compares the FAIRe2MDT wrapper with the script run by hand on
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
  account. Which of these, and who maintains them, is still to be decided.
- **Language model optional.** Every tool works without one. A model's answers are marked as
  such, and only a person's answers count as confirmed.
- **Credit and ownership** (7 November 2026). Oliver Berry (CSIRO) wrote the Galaxy tools for the
  upstream FAIRe tools and developed the FAIRe mapper, with Claude (Anthropic). Each tool's
  `<creator>` block names him, and its help credits both. Each upstream tool stays with its own
  developers. Future maintenance is to be decided (see GitHub home above).

## Steps common to all tools

`docs/faire_tools_guide.md`
(the guide to all the tools) and `docs/faire_mapper_inputs.md` (the guide to the FAIRe mapper's
inputs) are the texts the tools show in Galaxy, for reuse on the Galaxy eDNA Lab pages.
`docs/ena_submission_from_galaxy.md` looks at the IUC's ENA Upload tool as a way to submit FAIRe
data to ENA from inside Galaxy.

1. Agree with the upstream authors that the wrappers can be published, and report the issues listed
   in each README, and ask for tagged releases. (All the upstream repositories now have licence
   files: FAIRe-ator, the FAIRe checklist and FAIRe2MDT added theirs on 11 November 2026.)
2. Choose a ToolShed owner account (the GitHub home is FAIR-eDNA/FAIRe-Galaxy). Fill in `owner`
   in each `.shed.yml`, and add maintainers to each `<creator>` block.
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

Tests were last run together on 4 November 2026, after the shared guide was added, with planemo
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
