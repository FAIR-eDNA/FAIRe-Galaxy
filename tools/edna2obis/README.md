# edna2obis Galaxy wrappers

Two Galaxy tools that turn a FAIRe metadata workbook and per-assay ASV or OTU tables into Darwin
Core tables for OBIS and GBIF:

| Tool | Galaxy ID | Input | Output |
|---|---|---|---|
| edna2obis: match taxa | `edna2obis_match_taxa` | Per assay: assay name, taxonomy table; WoRMS or GBIF | Mapping table for review (`taxa_mapping_INFO` layout plus `assay_name`), log |
| edna2obis: build Darwin Core tables | `edna2obis_dwc` | FAIRe workbook; per assay: taxonomy and abundance tables; a reviewed mapping table (or a WoRMS or GBIF lookup) | Darwin Core archive (zip), occurrence, DNA-derived data, eMoF, event core, eml.xml, taxa mapping, HTML report, config, log |

Upstream: [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) at commit
`a3bc89050bcee12b482237cb2e3bb5c3c276debc` (26 Oct 2026, "Revise readme"). MIT licence.

## Status

- `planemo lint`: passes with no warnings.
- `planemo shed_lint`: passes except for the placeholder owner in `.shed.yml`; its ToolShed check
  needs network access and could not run here.
- `planemo test`: the 9 tests of *build Darwin Core tables* pass in Galaxy 25.0 (results at the end
  of this file). They run offline, with mapping tables made for the tests.
- The 2 tests of *match taxa* need internet access to WoRMS and GBIF. They passed on GitHub on 6
  November 2026 (Galaxy 26.1, containers), after the two fixes the first run there showed (pygbif
  0.6.5, and Excel output to a `.dat` path). This workspace cannot reach either service, and both
  tests fail here with the tool's "could not reach the ... API" message, as they should. The matching code path was checked
  with stand-ins for the services (see "Checks without network access").
- Not yet tried with an Australian dataset, a real WoRMS or GBIF lookup, or an IPT.

## Files

| File | Purpose |
|---|---|
| `edna2obis_match_taxa.xml`, `edna2obis_dwc.xml` | Galaxy tool definitions |
| `macros.xml` | Shared version, requirements, assay and API inputs, help and citations |
| `edna2obis_galaxy.py` | Galaxy driver (subcommands `match` and `build`; see below) |
| `main.py`, `data_mapper.yaml`, `src-v3/` (Python files) | Upstream code, copied unchanged |
| `raw-v3/eMoF_Fields_edna2obis.tsv` | Upstream eMoF template, copied unchanged (the tool's default template) |
| `normalise_faire.py` | Relabels FAIRe-ator assay columns by assay name; the same file as in `faire2qiime/` and `faire2ncbi/` |
| `LICENSE.upstream` | Upstream MIT licence |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |
| `test-data/` | Test workbooks, tables, mapping tables, EML files (see below) |

`main.py` and `data_mapper.yaml` sit at the top of the folder and the modules in `src-v3/`, as
upstream has them, because `main.py` imports from `src-v3`. Not included: `taxamapper.py` (see
Decisions), `src-v3/create_asv_seq_taxa_obis.sh` (QIIME 2 conversion), `config.yaml` and the example
configs (the driver writes the config), `EML_config.yaml` and `contacts.yaml` (they describe NOAA's
example dataset and staff; the help links to upstream instead), `images/`, `processed-v3/` and the
example data apart from the eMoF template.

## What the wrapper adds

The driver imports the upstream modules and runs them in a working folder of the job, because
upstream reads `config.yaml` and `data_mapper.yaml` from the current folder. It writes upstream's
`config.yaml` from the form. No upstream file is changed.

1. **Taxonomy lookup separated from building the archive.** *match taxa* runs the pipeline's own
   taxonomy step (`assign_taxonomy`, `create_taxa_assignment_info`, the GBIF de-duplication and the
   `mark_selected_*` functions) once per assay, and adds an `assay_name` column to the
   `taxa_mapping_INFO` table. *build Darwin Core tables* can take that table, after review, instead
   of calling the API. Upstream has no way to reuse a mapping: the full pipeline always calls the
   API. The driver replaces the two functions that would call it
   (`WoRMS_v3_matching.get_worms_match_for_dataframe` and
   `GBIF_matching.get_gbif_match_for_dataframe`) with one that returns the same
   `{'main_df', 'info_df'}` structure from the selected rows of the table. Everything after that
   (upstream's *incertae sedis* rules, column order, `taxa_mapping_INFO`, selection marking) is
   upstream code. Two details make this work:
   - `assign_taxonomy` calls `importlib.reload` on the matcher modules, which would undo the
     replacement; in this mode the driver gives that module a `reload` that returns the module
     unchanged (a fresh job has nothing to reload).
   - The pyworms and pygbif functions (and `urllib.request.urlopen`) are replaced by ones that stop
     the run, so no API call can happen with a mapping table.
2. **Mapping table checks.** Each name with reads needs exactly one selected row (per assay, when
   the table has `assay_name`; otherwise per name). The tool stops and lists names that are missing,
   that have no selected row, or that have two selected rows with different taxa. A table without
   `assay_name` (for example upstream's own `taxa_mapping_INFO_*.xlsx`) is also accepted.
3. **Unreachable API.** Upstream reports failed requests as *incertae sedis* without saying so
   (issues below). Before matching, the driver sends one request with a 30-second timeout and stops
   with a plain message if the service cannot be reached. During matching it wraps the pyworms and
   pygbif functions upstream calls and writes every failed request to a file (worker processes are
   forked, so they inherit the wrappers; the driver sets the `fork` start method). If any request
   failed, the tool stops instead of writing incomplete results. It also stops if one of those
   calls raises a TypeError, which means upstream's call does not fit the installed library (as
   with pygbif 0.6.6, issues below); upstream would log a warning and go on with fewer matches.
   Any error status from GBIF's match or search counts as a failed request, as both answer every
   name (so if GBIF withdraws the v1 matching service that pygbif 0.6.5 uses, the tool stops); a
   404 from `name_usage` (an unknown key) does not.
   WoRMS lookups go over HTTPS:
   pyworms has WoRMS's address as plain HTTP (`http://www.marinespecies.org/rest/`, port 80) in
   every version on conda-forge, so before the check the driver points pyworms's `worms_url()` at
   `https://www.marinespecies.org/rest/`, which WoRMS also serves. Jobs then need only HTTPS (port
   443), and the log names the address used.
4. **FAIRe-ator workbooks.** `normalise_faire.py` relabels `assay1`, `assay2` ... columns, or copies
   `project_level` into a column named by the assay. Upstream reads `assay1`, `assay2` columns
   itself, but stops on single-assay workbooks ("No data to combine").
5. **Workbooks with analysisMetadata sheets** (FAIRe-NOAA). Upstream then uses the sheets'
   `analysis_run_name` as the run name. The driver takes it from the one sheet for each assay when
   the form leaves it empty, checks a given name against the sheets, finds the term_name column,
   and leaves out sheets for analyses not in the run (see the fallback issue below).
6. **Tables.** Taxonomy and abundance tables may be tab-separated, comma-separated or Excel, with
   rows above the field names (FAIRe templates have two `#` rows) and other sheets (FAIRe's
   *Drop-down values*). The driver copies each to TSV with the field names on row 1. Abundance
   columns named by `samp_name` are renamed to the `lib_id` of that sample's run for the assay
   (upstream does this too, but only after removing controls by `lib_id`, so controls stayed in).
7. **eventDate.** Excel date cells are written as ISO 8601 text (`2021-09-14T11:00:00`); upstream
   would write `2021-09-14 11:00:00`. Text dates are checked before the run. Year-first ISO 8601
   values (dates, date-times, intervals) and FAIRe missing-value terms pass through; `2019/06/07`
   is rewritten as `2019-06-07`. Dates written day or month first (`7/6/19`) stop the run with a
   list of the samples, unless the form says how to read them: day first (as in Australia) or month
   first (as in the USA). They are then rewritten as ISO 8601 and the log says how many. A date that
   is not valid in the chosen order (`7/15/19` read day first) stops the run. Two-digit years 00 to
   69 are read as 2000 to 2069. Values giving only a year or a month (`2019-06`) get a warning,
   because upstream writes them as the first day (`2019-06-01`).
8. **Checks before running.** Each assay must have a projectMetadata column and appear in
   experimentRunMetadata; each set of tables needs its own analysis run name (part of every
   occurrenceID).
9. **EML.** Three choices: a short form (title, abstract, creator and contact, ORCID, licence,
   keywords, dates, descriptions), the user's `EML_config.yaml`, or none. With a YAML file,
   `contacts_path` is removed (it could name any file on the server, and upstream also searches
   eight parent folders for `contacts.yaml`); contacts come only from the optional contacts file on
   the form. Free text reaches the driver through Galaxy's inputs JSON file, unsanitised, and never
   the command line.
10. **Plain errors.** Upstream records eMoF and EML failures as warnings and finishes; it also
    catches errors in the taxonomy step and carries on. The tool stops when edna2obis reports any
    error or a requested file is missing, and prints the reason (no traceback). The eMoF error for
    shared `lib_id` values gets an explanation and the values concerned.
11. **Darwin Core archive.** Upstream writes the files but no zip. The driver zips `meta.xml`, the
    files it lists and `eml.xml`, under the names `meta.xml` uses.
12. **Tidy log.** Upstream's figlet banner, usage table, colour codes and spinner are replaced by
    plain output, and the browser is not opened. The report's warnings are listed in the log as
    plain text.
13. **Text values.** The workbook copy keeps every cell as upstream reads it (`na_values=[""]`,
    `keep_default_na=False`), so text such as `NA` or `N/A` stays text until the form's option
    handles it (item 14). Text starting with `=` also stays text (openpyxl would otherwise save it
    as a formula with no value). Before 9 November the copy emptied the first and lost the second; a
    station_id of `=Sta1` removed locationID from the occurrence core. An eventDate of `NA` kept as
    written stops the run with the tool's existing message for unreadable dates. Found with the
    differential check in `dev/normalise_faire_differential`.
14. **Text such as NA or N/A** (decided 9 November 2026). The form's new option replaces it
    with one of FAIRe's missing-value terms (FAIRe checklist, section 4.3.3): `missing: not
    provided` by default, or `missing: not collected`, `not applicable` or `missing: restricted
    access`. The log lists how many cells of each field were replaced. It can also keep the text as
    written, as upstream does, or stop and list the cells. Only values are changed (rows below the
    field names, and projectMetadata's project_level and assay columns); `None` is left as
    written, as it can be a real answer. An eventDate of `NA` is replaced like any other value, so
    it no longer stops the date check.
15. **Values as written through upstream's own reads** (9 November 2026). Upstream reads the
    workbook without `dtype`, so a column of IDs written as text (`001`) becomes numbers, and it
    writes the occurrence table to a file and reads it back with pandas' defaults twice (in the
    taxonomy step and in its final file check, which writes a table again when it drops an empty
    column), turning `001` into `1` and NA-like text into empty cells. While upstream runs, the driver
    sends these reads to versions that keep each cell's own type, or read the tables as text
    (`keep_values_as_written`). No upstream file is changed, and the run stops if upstream no
    longer reads that way. On the test inputs the outputs are the same as before, except eMoF
    diss_oxygen, which reads `190` as in the workbook, where it read `190.0`.

Python warnings: Galaxy sets `PYTHONWARNINGS=ignore`. edna2obis reports through its HTML reporter,
`print()` and `logging`, not the warnings module, so nothing is lost.

## Decisions

- **Pipeline step, not `taxamapper.py`.** `taxamapper.py` matches a list of names with one dummy
  assay, so the per-assay *ignore species-level names* setting and the rank depth taken from each
  taxonomy table would not apply, and its candidate limit differs from the pipeline. Running the
  pipeline's taxonomy step per assay gives the same selection as a full run. Names shared by two
  assays are looked up once per assay.
- **Mapping table layout**: upstream's `taxa_mapping_INFO` columns plus `assay_name`, tabular by
  default (viewable and editable in Galaxy), Excel optional.
- **The build tool can also look names up** (needs internet), for users who do not want to review.
  Its Galaxy tests cover only the offline path.
- **Defaults** are upstream's in-code defaults (what `load_config` uses when a setting is left out),
  not the values in upstream's example `config.yaml`: WoRMS marine taxa only, no limit on walking up
  the taxonomy string, no higherClassification, 3 GBIF candidates, GBIF selection by confidence.
  *Include non-marine taxa* is on the main form because Australian freshwater and estuarine data
  will need it.
- **Parallel requests**: 1 by default, at most 4 (upstream uses up to 10, or all CPUs). Galaxy
  Australia advised (November 2026) that jobs on the same node share WoRMS's and GBIF's request
  limits, and that going over a limit can make jobs fail. Retrying after a refused request would
  help further; that is a change for upstream.
- **Defaults for samples**: controls are rows with `samp_category` *negative control*, *positive
  control* or *PCR standard* (upstream's defaults, with PCR standard added on 6 November 2026, as
  FAIRe's three control categories); locationID from `line_id` and `station_id` (upstream's
  defaults).
- **Run names** default to the assay name. They are part of every occurrenceID
  (`project_id:run:lib_id_occ_featureid`), so the help asks users to keep them stable.
- **Not on the form**: splitting outputs by `short_name` (would need collection outputs), the PR2
  local reference database for WoRMS, separate TSV metadata files, the performance log and the
  FAIRe-NOAA checklist fallback.
- **HTML report kept.** It is useful for its previews and warnings. Galaxy sanitises HTML outputs,
  which removes the sample map (Leaflet from unpkg.com, tiles from ArcGIS); the logos are broken
  outside the repository anyway.
- **eMoF template**: upstream's, as default; a custom template or none can be chosen.
- **Requirements** pinned to the versions tested here, all from conda-forge: python 3.12, pandas
  2.2.3, numpy 2.5.4, openpyxl 3.1.5, pyyaml 6.0.3, pyworms 0.3.0, pygbif 0.6.5, multiprocess
  0.70.19, requests 2.34.2, rich 15.0.0, pyfiglet 1.0.3. Upstream's `notebook`, `nb_conda_kernels`
  and `pytz` are not used by the code. pygbif is held at 0.6.5 (November 2024), the last release
  whose `name_backbone` takes the arguments upstream passes (issues below); the only change to
  pygbif's species functions in 0.6.6 is that one.

## Upstream issues to report

Evidence is in the test data, the local checks or the upstream code at the pinned commit.

- **GBIF matching needs pygbif 0.6.5 or earlier.** `GBIF_matching.py` calls
  `species.name_backbone(name=..., rank=..., strict=True)` and reads the v1 answer (`usageKey`,
  `confidence`). pygbif 0.6.6 (November 2025) moved `name_backbone` to GBIF's v2 matching service,
  with new argument names (`scientificName`, `taxonRank`) and a different answer. With 0.6.6 every
  call fails ("Session.request() got an unexpected keyword argument 'name'"), and upstream logs a
  warning and goes on without the backbone matches and their confidence values. Found in the first
  run with internet access (GitHub, 6 November 2026). Upstream does not pin pygbif.

- **Failed API requests become *incertae sedis* silently.** `get_worms_batch_worker` catches every
  exception and returns no matches; the GBIF worker logs a warning and moves on; higherClassification
  lookups return nothing. The run is reported as a success.
- **GBIF cache keeps failures.** Empty results, including those from failed requests, are saved in
  `gbif_matches_cache_v3.pkl` in the output folder and reused, so later runs in that folder never
  retry those names. (The cache is a pickle loaded from the output folder; safe only if nobody else
  can write there.)
- **WoRMS matcher keeps SILVA rank prefixes**: `d__Bacteria; p__Cyanobacteria` is looked up as
  "d Bacteria", "p Cyanobacteria" and so on, so these strings never match. The README says prefixes
  are removed; only the GBIF matcher removes them. The WoRMS matcher also deletes digits ("SAR11
  clade" becomes "SAR clade").
- **Controls stay in when abundance columns are sample names**, as in the GOMECC-4 example's otuRaw
  files: controls are removed by `lib_id` before `samp_name` columns are mapped to `lib_id`. With the
  test tables, the negative control's 13 occurrences stayed in (35 records instead of 22, with the
  warning "lib_id(s) in abundance table not in ERM").
- **Single-assay FAIRe workbooks fail** (assay values in `project_level`): "Failed to create
  occurrence core: No data to combine".
- **eMoF fails when one `lib_id` is used in two assays** (as in the GOMECC-4 example): the join to
  experimentRunMetadata ignores the assay, giving "Internal alignment error for source field
  'input_read_count': join frame length 57 != 35".
- **Errors reported as success.** eMoF and EML failures are warnings ("SUCCESS with WARNINGS" and the
  file missing); errors in the taxonomy step are caught and the pipeline carries on; a config that
  cannot be read ends with exit code 0.
- **Fallback that can duplicate data**: an analysisMetadata sheet with no `datafiles` entry takes
  the tables of the only entry with the same assay name (`occurrence_builder.py` lines 278 to 289),
  so two sheets for one assay and one set of tables give the same occurrences twice under different
  run names (from the code; not run).
- **Runs only from the repository folder**: `config.yaml`, `data_mapper.yaml` and `src-v3` are read
  relative to the current folder, and the occurrence column order reads `metadata_format` from
  `config.yaml` rather than from the config in use (`run_config_path`).
- **Dates.** Excel date cells reach eventDate as `2021-09-14 11:00:00`. Text dates are read with
  `pd.to_datetime`, which takes `7/6/19` month first (2019-07-06) but `13/6/19` day first, so a
  day-first column (as in Australian data) comes out partly swapped, without a warning. A year or a
  month on its own (`2019-06`) becomes the first day (`2019-06-01`). The wrapper's checks are in
  item 7 above.
- **Values change on the way through.** The sheets are read with `keep_default_na=False`, which
  keeps text such as NA, but without `dtype=str`, so a column of IDs written as text (materialSampleID
  `001`, `002`, `003`) reaches the occurrence core as 1, 2, 3 (pandas 2.2.3 and 3.0). The final file
  check (`final_output_validation` in `main.py`) then reads each output table back with pandas'
  defaults and, when a column is empty, drops it and writes the table again, emptying NA-like text:
  `N/A` in env_medium reached the DNA-derived extension and was then removed. The taxonomy step
  also reads the occurrence table back with pandas' defaults. Found 9 November; the wrapper works
  around all three reads (item 15).
- **Byte order marks.** Tables from which empty columns are dropped are rewritten as UTF-8 with a
  byte order mark; others are not.
- **HTML report**: workbook values are inserted without HTML escaping (`to_html(escape=False)`,
  `add_text`); the map loads scripts from unpkg.com; every run calls `webbrowser.open`.
- **Licences**: values other than `CC0`, `CC-BY` and `CC-BY-NC` silently get the CC0 text in
  intellectualRights.
- **Contacts file search** walks up eight parent folders for `contacts.yaml`, and `contacts_path`
  can name any file.
- **Species-level skipping differs**: WoRMS drops the last name when the string has as many names
  as the table has rank columns (7 without a Confidence column); GBIF when it has 6 or more.
- **Event core**: a sample event's sampleSizeValue is the read total of its first library only
  (GU190706-CTD11-220: 244495, the MiFish library; its Riaz library is left out).
- A tagged release for the current code and a conda package would help, as for the other FAIRe
  tools. pyworms (a separate project) has WoRMS's address as plain HTTP (the driver changes it to
  HTTPS) and retries each failed request 10 times, 5 seconds apart.

## Before deployment on Galaxy Australia

### Must do

1. **Run the *match taxa* tests with internet access** (not run here) and look up the names of an
   Australian FAIRe dataset in WoRMS and GBIF. Check the selected matches by hand, especially for
   SILVA-style 16S strings in WoRMS (issue above) and freshwater taxa with *Include non-marine taxa*
   off and on.
2. **Confirm network access** for these jobs: HTTPS to `www.marinespecies.org` and `api.gbif.org`.
   Galaxy Australia has confirmed that jobs have internet access. Port 80 is not needed (WoRMS
   lookups go over HTTPS since 6 November 2026). On 6 November 2026, Galaxy Australia's Upload tool
   fetched `https://www.marinespecies.org/rest/AphiaRecordByAphiaID/2` (and the same over plain
   HTTP): the record for Animalia, AphiaID 2, which is the record the driver's check asks for.
3. **Trial a publication**: load the zip into a test IPT (OBIS or GBIF), and run it through the GBIF
   data validator. Check the byte order marks, eventDate values and the eMoF units.
4. **Talk to the upstream authors (NOAA 'Omics, AOML).** Tell them about the wrapper and the issues
   above, offer the `normalise_faire.py` layout fix and the `samp_name` to `lib_id` renaming, and ask
   for a tagged release. The tool version is the commit date (`2026.10.26`).
5. ~~**Check the citation.**~~ Done 7 November: the Zenodo DOI `10.5281/zenodo.23667395`, upstream's
   own citation in the README of the pinned commit, resolves to *aomlomics/edna2obis: v3.2.0* (Willms
   B and Silliman K, published 26 October 2026, MIT licence), the release the wrapper uses.
6. **Fill in `.shed.yml`** (`owner`) and add the maintainers to the
   `<creator>` block in `macros.xml`; then publish to the Test ToolShed, and ask Galaxy Australia to
   install both tools in the eDNA lab next to the other FAIRe tools.

### Should do

7. ~~**Decide the default for *Include non-marine taxa*.**~~ Decided 7 November 2026: upstream's default (marine only) is kept.
8. **Write a short guide** in the eDNA lab: *FAIRe workbook → match taxa → review → build Darwin
   Core tables → IPT*.
9. **Add `short_name` splitting** (one archive per cruise or survey) as collection outputs, and the
   PR2 local reference database option, if users need them.
10. **Decide where the code lives long term** (conda package from a tagged release, as for the other
    wrappers).

## Test data

All files are under 50 KB. The two GOMECC-4 workbooks are the FAIRe2QIIME test workbooks; the
GU19-01 workbook is the FAIRe2NCBI one with sheets added. The tables were cut from the MIT example
data in [aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) (`raw-v3/`) by a script kept
outside the repository: for each assay, the 6 ASVs (5 for GU19-01) with most reads in the test
workbook's samples, plus one ASV seen only in a control.

- `faire_two_assays.xlsx`: GOMECC-4 generic FAIRe, FAIRe-ator layout (`assay1`, `assay2`), four
  samples (one negative control), eight runs, 16S and 18S. Some `lib_id` values are used in both
  assays, as in the full example.
- `faire_single_assay.xlsx`: the same samples, 16S only, assay values in `project_level`; one
  eventDate is an Excel date cell.
- `gomecc_16s_taxonomy.xlsx`: 7 rows of `taxaRaw_noaa-aoml-gomecc4_ssu16sv4v5-emp_20220613.xlsx`,
  keeping its two `#` rows above the field names. `gomecc_16s_abundance.tsv`: the same ASVs from
  `otuRaw_..._ssu16sv4v5-emp_20220613_16S-Amplicon_PE250.xlsx`, columns by `samp_name`.
- `gomecc_18s_taxonomy.tsv` and `gomecc_18s_abundance.csv`: 7 ASVs from the 18S taxaRaw and otuRaw
  files (columns by `samp_name`).
- `faire_noaa_analysis_sheets.xlsx`: FAIRe-NOAA layout (GU19-01, two 12S assays, five samples of
  which two are negative controls, ten runs), with the two analysisMetadata TSVs of
  `FAIRe_NOAA_example_dataset_small` added as sheets `analysisMetadata_mifish` and
  `analysisMetadata_riaz`.
- `faire_text_values.xlsx`: `faire_two_assays.xlsx` with station_id `=Sta1` for
  `GOMECC4_27N_Sta1_DCM_A`, station_id and env_medium `N/A` for `GOMECC4_27N_Sta1_DCM_B`, and
  materialSampleID `001` to `004` as text (tests text values, items 13 to 15). Written by
  `dev/normalise_faire_differential/make_testdata.py`.
- `gu1901_mifish_*.tsv`, `gu1901_riaz_*.tsv`: 6 ASVs each from that example's `asvTaxaFeatures` and
  `table` files (columns by `lib_id`).
- `emof_template_sample_fields.tsv`: the header and the temp, chlorophyll, salinity and diss_oxygen
  rows of upstream's eMoF template.
- **Mapping tables made for the tests**: `test_mapping_worms_made_for_test.tsv` (GOMECC-4, with
  `assay_name`, two candidates for one name), `test_mapping_gbif_made_for_test.tsv` (GU19-01,
  without `assay_name`, two candidates for one name) and `test_mapping_two_selected.tsv` (two
  selected rows for one name). **They are not WoRMS or GBIF output.** Names come from the test
  taxonomy tables; ranks were filled only where the taxonomy string names them; identifiers are
  `urn:lsid:example.org:made-for-test:N` and `gbif:made-for-test-N` (plus upstream's fixed
  *incertae sedis* LSID); every row has `match_type_debug` set to `made_for_test_not_from_WoRMS` or
  `made_for_test_not_from_GBIF`.
- `eml_config_test.yaml` and `contacts_test.yaml`: made for the tests, with a fictional person and
  example.org addresses. The EML file sets `contacts_path` to check that it is ignored.

## Running the tests

```bash
pip install planemo
planemo lint edna2obis/
planemo test edna2obis/edna2obis_dwc.xml          # offline
planemo test edna2obis/edna2obis_match_taxa.xml   # needs internet access to WoRMS and GBIF
```

### Checks without network access

Run directly with the driver in a scratch folder, not as Galaxy tests (on 3 November 2026):

- *match taxa* with no route to WoRMS or GBIF (name lookup failing, and a proxy refusing the
  connection): stops after about 1.5 seconds with "could not reach the WoRMS API at
  www.marinespecies.org: the server name could not be looked up. Looking up names needs internet
  access ...", no traceback, no mapping table.
- *match taxa* with stand-ins for `pyworms.aphiaRecordsByMatchNames` (made-up records with
  example.org identifiers, not shipped): writes the mapping table with `assay_name`, one selected
  row per name and assay, and candidates kept for review; when the stand-in raises an error in a
  worker process, the tool stops with "1 request(s) to the WoRMS API failed during matching".
- Round trip: that stand-in table, with one selection changed by hand, given to *build Darwin Core
  tables*: the changed selection reaches the occurrence core.
- An EML file without a contact email: stops with "Missing required EML fields: Contact email is
  required".
- WoRMS over HTTPS (6 November 2026, pyworms 0.3.0): with `requests.get` replaced by a stand-in
  that records each address, the reachability check and upstream's three pyworms calls (after the
  module reload that `assign_taxonomy` does) all went to `https://www.marinespecies.org/rest/`.
- Two fixes from the first run with internet access (6 November 2026): an Excel mapping table is
  written to a path ending `.dat`, as Galaxy gives (pandas refused it before, so the GBIF test,
  which asks for Excel, failed at the end); and with pygbif 0.6.6, upstream's `name_backbone` call
  is recorded and the tool stops with "1 call(s) to the GBIF library failed because the call does
  not fit the installed version". With stand-ins that answer 404, a failed `name_backbone` call is
  recorded and stops the tool; a 404 from `name_usage` is not recorded.

## planemo test results

Run on 3 November 2026 with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (the versions under Decisions). 11 tests: the 9 offline tests passed; the 2
tests that need WoRMS and GBIF failed because this workspace cannot reach them, each with the
tool's own message (exit code 1, no traceback). The build tool's tests were run again after the
eventDate checks were added (tests 8 and 9; tests 2 and 5 now read their US dates month first).
All 11 were run again on 6 November 2026, after WoRMS lookups moved to HTTPS, with the same results.
The build tool's 12 tests all passed on 9 November 2026, with the text-values tests (items 13 to 15).

| Tool | Test | Checks | Result |
|---|---|---|---|
| edna2obis_dwc | 1 | FAIRe-ator layout, two assays, `samp_name` columns renamed to `lib_id`, controls left out (22 rows), xlsx taxonomy with `#` rows, CSV abundance, WoRMS mapping by assay (the unselected candidate is not used), custom eMoF template (88 rows), EML from the form (title from projectMetadata, CC BY 4.0, ORCID), zip members, ISO eventDate | passed |
| edna2obis_dwc | 2 | FAIRe-NOAA layout with analysisMetadata sheets (one run name taken from its sheet, one given), GBIF mapping without `assay_name`, Event core (3 sample and 6 library events), edna2obis's eMoF template, EML from YAML with a contacts file (`contacts_path` ignored), US dates read month first (4 rewritten as ISO 8601) | passed |
| edna2obis_dwc | 3 | Single assay in `project_level` (fails in upstream alone), Excel date cell, no eMoF, no eml.xml (meta.xml names neither) | passed |
| edna2obis_dwc | 4 | edna2obis's eMoF template with `lib_id` values shared by two assays: stops, explains and lists them | passed |
| edna2obis_dwc | 5 | Mapping table without the names of the tables: stops and lists the 5 names with their assay | passed |
| edna2obis_dwc | 6 | Two selected rows with different taxa for one name and assay: stops and names it | passed |
| edna2obis_dwc | 7 | Assay not in the workbook: stops and lists the workbook's assays | passed |
| edna2obis_dwc | 8 | US dates (`7/6/19`) at the default setting: stops and lists the samples and values | passed |
| edna2obis_dwc | 9 | The same dates read day first: stops because `7/15/19` has no month 15 | passed |
| edna2obis_dwc | 10 | Text values kept as written: `=Sta1` and `N/A` in station_id reach locationID, materialSampleID `001` keeps its zeros, and `N/A` in env_medium reaches the DNA-derived extension; the log counts the NA-like cells | passed |
| edna2obis_dwc | 11 | Default: `N/A` replaced with `missing: not provided` (locationID `27N_missing: not provided`, env_medium), with the replacements listed in the log | passed |
| edna2obis_dwc | 12 | NA-like text with *stop*: stops and lists the 2 cells | passed |
| edna2obis_match_taxa | 1 | WoRMS, two assays (16S without species level, 18S), tabular output | passed on GitHub with internet access (6 November 2026); failed here: "could not reach the WoRMS API at www.marinespecies.org: the server name could not be looked up" (needs internet) |
| edna2obis_match_taxa | 2 | GBIF, one assay, Excel output | passed on GitHub with internet access (6 November 2026, after the fixes); failed here: "could not reach the GBIF API at api.gbif.org: the server name could not be looked up" (needs internet) |
