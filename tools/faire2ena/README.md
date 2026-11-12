# FAIRe2ENA Galaxy wrappers

Two Galaxy tools that turn a FAIRe metadata workbook into the XML files ENA needs:

| Tool | Galaxy ID | Input | Output |
|---|---|---|---|
| FAIRe2ENA: samples | `faire2ena_sample` | FAIRe workbook (.xlsx) | SAMPLE XML, SUBMISSION XML, log |
| FAIRe2ENA: experiments and runs | `faire2ena_run` | FAIRe workbook, ENA sample receipt | EXPERIMENT XML, RUN XML, SUBMISSION XML, log |

Upstream: [FAIR-eDNA/FAIRe2ENA](https://github.com/FAIR-eDNA/FAIRe2ENA) at commit
`29d0c98669a3ad9ba1c855b3dbf32d71e9e03c0c` (12 Nov 2025, the latest on `main` as of 3 Nov 2026). MIT licence.

## Status

- `planemo lint`: passes with no warnings.
- `planemo shed_lint`: passes except for the placeholder owner in `.shed.yml`.
- `planemo test`: all tests pass in Galaxy 25.0 (summary at the end of this file).
- ENA's test server, 11 November 2026: three SEA-MES samples submitted through the test Webin
  Portal were checked by ENA and refused for missing units and an "Unknown" value. With item 11
  below, ENA accepted them the same day (`dev/faire2ena_ena_trial/README.md`). Experiments and runs
  are not yet tried there.

## Files

| File | Purpose |
|---|---|
| `faire2ena_sample.xml`, `faire2ena_run.xml` | Galaxy tool definitions |
| `macros.xml` | Shared version, requirements, inputs and citation |
| `faire2ena_sample.py`, `faire2ena_run.py` | Upstream scripts, copied unchanged |
| `faire2ena_galaxy.py` | Galaxy driver that imports the upstream scripts (see below) |
| `LICENSE.upstream` | Upstream MIT licence |
| `test-data/` | Test workbook and a made-up ENA receipt (see below) |
| `faire_guide.xml` | The guide shown at the end of every FAIRe tool's help (`@HELP_FAIRE_GUIDE@`); a copy of `dev/faire_guide/faire_guide.xml`, updated by `dev/faire_guide/sync.py` |
| `LICENSE` | MIT licence for the wrapper code in this folder (upstream files keep their own licence) |
| `.shed.yml` | ToolShed metadata (owner still to fill in) |

`upload_reads.py` is not included. It takes the Webin password as a command-line argument, and
Galaxy would store that in the user's history.

## What the driver adds

The upstream scripts are imported as they are. The driver (`faire2ena_galaxy.py`) runs extra steps
before and after them:

1. **Collection dates.** ENA's date pattern does not accept time zone offsets written as `+hh:mm`.
   The upstream script replaces every such date with "not provided". In the GOMECC-4 example
   workbook this happens to all 502 samples. Australian data with offsets such as `+08:00` or
   `+09:30` would be affected the same way. The driver converts these to UTC (for example
   `2021-09-14T11:00-04:00` becomes `2021-09-14T15:00Z`). Users can turn this off.
2. **Excel date cells.** If eventDate is stored as an Excel date, the upstream script crashes
   (`TypeError`). The driver turns these into ISO text first.
3. **Sample taxon.** Upstream hard-codes taxon 408172 (marine metagenome). The tool offers
   marine, freshwater and aquatic metagenome, or any NCBI taxon ID.
4. **Mandatory fields.** If a real sample is missing a mandatory field that has no default (for
   example `env_broad_scale` or `geo_loc_name`), upstream stops with a bare `KeyError`. The driver
   lists every affected sample and FAIRe term in one message.
5. **Run checks.** Before writing runs, the driver stops if any included row has an empty file
   name, a missing or malformed MD5, or a repeated `lib_id`. Upstream would write `filename="nan"`
   or `checksum="nan"`, or aliases that ENA rejects as duplicates.
6. **One assay at a time.** Upstream's `--assay` option adds a suffix to every row without
   filtering, so a 16S run could be labelled `_COI`. The tool filters to the chosen assay and then
   adds its name as the suffix.
7. **Sequencing runs.** The run tool can also be limited to some sequencing runs (seq_run_id), as
   FAIRe2NCBI SRA can. A library sequenced in two runs (as in the GOMECC-4 workbook, where seven 16S
   controls keep their lib_id in a second run) then goes in two submissions, one per run. ENA still
   needs each alias to be unique in your Webin account, so the second run's rows need their own
   lib_id.
8. **Libraries that hold several assays.** When amplicons are pooled before indexing, one set of
   fastq files holds several assays, and experimentRunMetadata has a row for each assay with the
   same sample and files. The driver writes one experiment and run for each such library, as ENA
   takes each set of files once. Rows that share a lib_id but not their files still stop the run
   with advice. Found in the trial on CSIRO's SEA-MES 16S and COI data. FAIRe defines a library as
   "an amplicon of a sample with unique MIDs", so the FAIRe mapper writes lib_id as the library
   name, assay_name and seq_run_id (`M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12`); the aliases are
   the library's own name, with the assay and run taken off again (`M097_16SFish_LerayCOI`), and
   the run, then the whole lib_id, kept where names would repeat. A lib_id given to several assays
   with the same files is still accepted, with a note.
9. **FTP folder.** If the reads were uploaded into a folder of the Webin upload area, the run XML
   must include that folder in each file name. The tool adds it.
10. **SUBMISSION XML.** Both tools also write the ADD action file that the Webin REST service needs.
11. **ENA's units and numbers** (11 November 2026, from the ENA test-server trial). ENA's water
    checklist (ERC000024) wants these attributes as plain numbers with a unit: temperature (ºC),
    salinity (psu), sample storage temperature (°C), amount or size of sample collected (L, m3, g,
    kg or m2) and sample volume or weight for DNA extraction (mL, mg or g). Upstream adds no unit to
    the first four, writes the sample size as text ("1540 ml") labelled in litres whatever its unit,
    and writes "Unknown" for an empty size. The driver takes FAIRe's units (the checklist gives
    temp and samp_store_temp in degrees Celsius and salinity in psu; samp_size_unit and
    samp_vol_we_dna_ext_unit for the others), converts between units where needed (1540 mL becomes
    1.54 L), and leaves out a value that is not a number or has no unit (all five are optional
    in ERC000024), listing each in the log. FAIRe's missing-value terms, such as *not applicable:
    control sample*, are left out without a note. It also removes upstream's second, misspelt copy
    of the extraction volume. The units are added while upstream writes each sample, and the run
    stops if upstream no longer writes them the way the driver expects.
    Extended on 12 November 2026, when SEA-MES 18S samples showed the same fault in the chemistry
    fields: chlorophyll (mg/m3), light intensity (lux), suspended particulate matter (mg/L),
    turbidity (NTU), total depth of water column and elevation (m), from FAIRe's fixed units; pH as a
    number with no unit; and 16 concentrations with a FAIRe unit term (dissolved oxygen, nitrate,
    nitrite, dissolved and particulate carbon and nitrogen, organic matter), in ERC000024's units. A
    concentration is converted only when a power of ten separates the units (µM to µmol/L, mmol/kg
    to µmol/kg, mg/L to µg/L); per litre and per kilogram, or moles and grams, are not converted, so
    a nitrate in µmol/kg is left out of ENA's µmol/L and listed. Water current is left out, as FAIRe
    gives m/s and ENA takes m3/s or knots. Upstream's second copies of five concentrations (for
    example *dissolved_oxygen*, beside *dissolved oxygen*) are removed.

## Upstream issues to report

These are worth raising with the FAIRe2ENA authors. If they are fixed upstream, the driver can shrink.

- Offset datetimes are replaced with "not provided" (item 1 above).
- Excel date cells cause a `TypeError` (item 2).
- Missing mandatory fields without a default cause a `KeyError` (item 4).
- `samp_vol_we_dna_ext` is written twice: once as *sample volume or weight for DNA extraction*
  and once under the misspelt tag *sample volume for weight for DNA extraction*.
- No units for temperature, salinity, sample storage temperature and the extraction volume, the
  sample size written as text with a fixed unit of litres, and "Unknown" for an empty value
  (`combine_value_with_unit`, and `if samp_size:` is true for an empty cell, which pandas reads as
  NaN). ENA refuses all of these (item 11).
- The same for the concentrations with a FAIRe unit term: `unit_mappings` writes "<value> <unit>"
  or "Unknown", in place of the plain value for nitrate and nitrite and as a second attribute with
  an underscore name for five others (*dissolved_oxygen*). Chlorophyll, turbidity and the other
  fields with a fixed FAIRe unit get no UNITS (item 11).
- *sizefraction lower threshold* and *sizefraction upper threshold* do not match the checklist's
  labels (*size-fraction lower threshold*, *size-fraction upper threshold*), so ENA keeps them as
  extra attributes, without units. FAIRe's size_frac_low and size_frac also seem to map the wrong
  way round: FAIRe's size_frac is the filter that retains the sample (ENA's lower threshold).
  Not yet changed in the driver.
- The "Generated ENA XML with N samples" message counts XML lines, not samples.
- Empty `filename2` or checksum cells become `nan` in the RUN XML (item 5).
- `--assay` adds a suffix without filtering rows (item 6).
- Taxon, checklist (ERC000024 water), platform (Illumina) and library layout (paired) are fixed.
  A tagged release and a pip or bioconda package would also help (see below).

## Before deployment on Galaxy Australia

### Must do

1. **Talk to the upstream authors.** Tell them about the wrapper and the issues above. Ask for a
   tagged release, so the tool version refers to something stable. Upstream has no releases, so the
   version is currently the commit date (`2025.11.12`).
2. **Check the three taxon IDs in a browser.** Checked from here on 5 November 2026: NCBI's
   Taxonomy pages open only some of the time (a browser check), and NCBI's API and ENA's taxonomy
   service cannot be reached. Web searches for *marine metagenome* (408172), *freshwater
   metagenome* (449393) and *aquatic metagenome* (1169740) return the NCBI Taxonomy page of each
   ID, but the pages themselves did not open. Opening
   `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=408172` (and 449393, 1169740) in a
   browser takes a minute; ENA also needs each to be submittable, which
   `https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/408172` shows.
3. **Do an end-to-end test on the ENA test server** (`wwwdev.ebi.ac.uk`) with a real Australian
   dataset, for example an OceanOmics or CSIRO FAIRe workbook: submit samples, upload the receipt to
   Galaxy, upload a few fastq files, submit experiments and runs. The test data here uses invented
   accessions and checksums, so it only proves the XML is well formed. Started 11 November 2026 with
   three SEA-MES samples (`dev/faire2ena_ena_trial/README.md`): ENA accepted the samples, after
   item 11, through the Webin Portal. Experiments and runs are next.
4. **Fill in `.shed.yml`.** Set `owner` (the ToolShed account that will publish it). Add the
   maintainers to the `<creator>` block in `macros.xml`.
5. **Publish to the ToolShed.** Use the Test ToolShed first (`planemo shed_create` and
   `planemo shed_update`), then the main ToolShed.
6. **Ask Galaxy Australia to install it.** Ask the Galaxy Australia team how they want install
   requests made for the eDNA lab. Suggest a section such as *eDNA data submission* in the
   tool panel.

### Should do

7. **Decide where the code lives long term.** Bundling the upstream scripts is fine for the
   ToolShed, but the IUC (the Galaxy community that maintains most shared tools) expects tools to
   come from a conda package. A bioconda recipe needs a tagged upstream release. If the FAIRe tools
   are consolidated into one package, this step is needed only once.
8. **Write a short Galaxy Training Network style tutorial** or a page in the eDNA lab that walks
   through the two-step ENA workflow, including how to get MD5 checksums and upload reads.
9. **Look at submitting from inside Galaxy.** The ToolShed has an ENA upload tool based on
   ena-upload-cli that keeps Webin credentials in the user's Galaxy preferences. Check whether it
   suits Galaxy Australia; if so, these XML files (or tables derived from them) could feed it, and
   users would not need curl.

### Could do later

10. Support other ENA checklists (soil, sediment, host-associated). This needs new field mappings
    upstream.
11. Support single-end runs and other platforms.
12. Compute MD5 checksums in Galaxy when the reads are already in the user's history.

## Test data

`test-data/faire_two_assays.xlsx` is a cut-down copy of the GOMECC-4 generic FAIRe example in
[aomlomics/edna2obis](https://github.com/aomlomics/edna2obis) (MIT): four samples (three
seawater samples and one negative control) and their eight runs across two assays (16S and 18S).
Changes from the source:

- One eventDate is stored as an Excel date, to test that path.
- `checksum_filename` and `checksum_filename2` are filled with MD5s of the file names, not of real
  files.

`test-data/faire_shared_library.xlsx` is the same workbook with each 18S run given the lib_id,
file names and checksums of the same sample's 16S run, so each library holds both assays.
`test-data/faire_amplicon_libraries.xlsx` has the same libraries with one lib_id per amplicon
(library name, assay_name and seq_run_id), the 18S rows given the run of the 16S rows whose files
they share.

`test-data/faire_ena_units.xlsx` is `faire_two_assays.xlsx` with an empty sample size for
GOMECC4_27N_Sta1_DCM_A, an empty extraction-volume unit for GOMECC4_27N_Sta1_DCM_B, and a storage
temperature of *ambient temperature* and a sample size of 2 kg for GOMECC4_BROWNSVILLE_Sta63_DCM_A
(tests item 11). Written by `dev/faire2ena_ena_trial/make_testdata.py`.

`test-data/ena_sample_receipt.xml` is a made-up ENA receipt with invented accessions
(ERS9999901 to ERS9999903) for the three seawater samples. The control is left out on purpose so
the tests check that unregistered samples are skipped.

## Running the tests

```bash
pip install planemo
planemo lint faire2ena/
planemo test faire2ena/
```

## planemo test results

Run on 3 November 2026, and again on 5 November with the sequencing-run filter and the joining of shared libraries, with planemo 0.75.47 against Galaxy `release_25.0`, with dependencies
resolved through conda (python 3.12, pandas 2.2.3, openpyxl 3.1.5). All tests passed.

| Tool | Test | Checks | Result |
|---|---|---|---|
| faire2ena_sample | 1 | Defaults: 4 samples, marine taxon, offset date converted to UTC, Excel date cell handled, SUBMISSION XML | passed |
| faire2ena_sample | 2 | Freshwater taxon; date conversion off gives upstream behaviour | passed |
| faire2ena_sample | 3 | Custom taxon ID | passed |
| faire2ena_sample | 1 (11 Nov) | Also ENA's units: ºC, psu, °C, sample size 1540 ml as 1.54 L, extraction volume in mL; no misspelt copy; the control's "not applicable" values left out | passed |
| faire2ena_sample | 1 (12 Nov) | Also dissolved oxygen 193.443 µmol/kg, chlorophyll in mg/m3, water depth in m; nitrate, nitrite and DIC in µmol/kg left out (ENA wants per litre) and listed; no *dissolved_oxygen* copy; the control's pH left out | passed |
| faire2ena_sample | 4 (12 Nov) | Also nitrate 0 µM as 0 µmol/L, dissolved oxygen 0.193443 mmol/kg as 193.443 µmol/kg, DIC 2033.19 mg/L as 2033190 µg/L, nitrate with no unit left out and listed | passed |
| faire2ena_sample | 4 | Empty sample size left out (no "Unknown"); extraction volume with no unit and storage temperature "ambient temperature" left out and listed in the log; 2 kg kept in kg | passed |
| faire2ena_run | 1 | One assay with suffix and FTP folder: 3 experiments, 3 runs, 6 files, unregistered control skipped, no `nan` | passed |
| faire2ena_run | 2 | All assays, each library holding both: 3 experiments and 3 runs, unregistered control skipped | passed |
| faire2ena_run | 3 | All assays with lib_id repeated with different files: stops with advice | passed |
| faire2ena_run | 4 | One sequencing run, all assays: 2 experiments, unregistered control skipped | passed |
| faire2ena_run | 5 | Unknown sequencing run: stops and lists the runs in the workbook | passed |
| faire2ena_run | 6 | Unknown assay name: stops and lists available assays | passed |
