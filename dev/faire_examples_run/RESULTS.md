# FAIRe example workbooks through the Galaxy FAIRe tools

Integration test, 3 November 2026. Tools from `tools/` as they were that day, copied into
`examples_run/tools/` and run there. Python: `python -I -W ignore`
(pandas 2.2.3, openpyxl 3.1.5, pydantic 2.7.0, pyyaml 6.0.3). `-W ignore` stands in for Galaxy's
`PYTHONWARNINGS=ignore`, which `-I` would otherwise drop. Each job ran in its own folder under
`examples_run/jobs/`, with the workbook symlinked as `input.xlsx`, as the XML `<command>` blocks do.
Nothing was submitted to ENA or NCBI and no credentials were used. The ENA run step used stand-in
receipts with invented accessions (`scripts/make_receipt.py`).

Form settings (from the XML defaults and tests):

- FAIRe-fier: checklist `auto`, not strict.
- FAIRe2ENA samples: centre CSIRO, dates converted, taxon 408172 (449393 for the NECR534 ponds).
- FAIRe2ENA runs: all assays, study PRJEB99999, Illumina NovaSeq 6000, no FTP folder.
- FAIRe2NCBI BioSample: empty mandatory fields `stop`, all samples, no duplicates field, dates
  converted, MIxS units, default title, all extra columns; organism marine metagenome
  (freshwater metagenome for NECR534).
- FAIRe2NCBI SRA: all runs, all, instrument from the workbook, link by sample_name.
- FAIRe2QIIME: sample ID `lib_id`, manifests on (`/path/to/sequences`), no suffix.

Where a default run stopped, I reran with the form changes a user would try next (marked "then").
Runs marked "diagnostic" used an edited copy of a workbook in `examples_run/derived/`.

## Results table

Key: **OK** exit 0 and output checks out; **OK, flawed** exit 0 but output has a problem;
**Stop** clean error from the wrapper (exit 1 or 2); **Crash** Python traceback;
n/a not run (targeted assay; FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME are for metabarcoding runs).
Letters give the cause: (a) workbook, (b) wrapper, (c) upstream.

| Workbook | FAIRe-fier | FAIRe2ENA samples | FAIRe2ENA runs | FAIRe2NCBI BioSample | FAIRe2NCBI SRA | FAIRe2QIIME |
|---|---|---|---|---|---|---|
| CPR_2015 (53 samples, 53 runs, 1 assay) | OK: valid, 0 issues | OK: 53 SAMPLE; samp_size "5 other:nautical miles" tagged UNITS L (c) | Stop: no filename/filename2 (a, ENA needs them) | Stop: *depth empty (c: reads maximumDepthInMeters only; minimumDepthInMeters = 10). Then fill "not collected": OK, 53 rows | Stop: instrument "MiSeq" not an NCBI value (a). Then instrument on form: Stop, no file names | OK, flawed: metadata 53 rows; manifest 53 rows, every path ends `/nan` (no file names) (c) |
| NECR534_GCN_metabarcoding (18, 18, 1) | Ran: invalid. 3 project + 19 sample errors (17 Excel date cells (c), "Not recorded", "BLAST", "6 bp difference" (a)) | OK: 18 SAMPLE; depth set to default 0 for all 18 (c); geo "UK" (a) | Stop: no MD5 checksums | Stop: *depth empty, no depth fields (a/c). Then fill: OK, 18 rows | Stop: "llumina MiSeq" (a). Then instrument on form: OK, flawed: 18 rows, design_description all "NA" (a + b) | Crash: `KeyError: '12S_V5'` (a + b) |
| verte_quadeloupe (22, 22, 4 assays) | Ran: invalid. Excel date cells (c), prepped_samp_store_sol free text (a) | OK: 22 SAMPLE; dates right but log says "converted 0" (b); depth default 0 (c) | Stop: no file names | Stop: 6 groups of identical samples. Then assay_name as the duplicates field: Stop, 6 groups (13 samples) remain (a: identical in every field) | Stop: "MiSeq" (a). Then instrument on form: Stop, no file names | OK, flawed: 4 assays share one file name, 3 overwritten; 4 of 22 rows kept (c + b). 5 manifests, all `/nan` |
| IOT-eDNA (271, 542, 2) | Ran: project invalid (ampliconSize "178/228" (a)); 89 lat/lon warnings, mostly false (c) | OK: 271 SAMPLE; dissolved oxygen written under two tags (c) | Stop: no file names; lib_id advice hidden (b) | OK: 271 rows; lat_lon rounded to 3 dp, 262 coordinate pairs become 166 (c) | Stop: "Illumina NovaSeq" (a). Then instrument on form: Stop, lib_id reused across assays (a); per assay: Stop, no file names | OK, flawed: metadata 271 + 271 rows; 4 manifests all `/nan`; COI sample IDs end "_16SFish" (a) |
| noaa-aoml-gomecc4 (502, 1008, 2) | Ran: invalid. 3 + 1921 errors, 4 + 981 warnings (2,909 rows, as in the FAIRe-fier README) | OK: 502 SAMPLE; 484 dates to UTC; 18 control dates become "not provided" (c) | Stop: no MD5 checksums; lib_id advice hidden (b) | Stop: 67 groups of identical samples. replicate_number: controls still identical. Then serial_number + fill: OK, 502 rows | Stop: library_ID repeated across assays (a, advice given). Then per assay: 18S OK, 500 rows; 16S Stop (lib_id repeated within assay); per seq_run: OK, 311 + 197 rows | OK: metadata 508 + 500, manifests 311/500/197; 16S IDs not unique (7 control lib_ids repeated) (a) |
| AEP_Fish_sedDNA (24, targeted) | Ran: project invalid (Excel mod_date (c); text decimals rejected (c)); sample passed although lat/lon are swapped (a) | n/a | n/a | n/a | n/a | n/a |
| EirwiniBurdekin (223, targeted) | Stop (exit 2): duplicate samp_name "missing: not collected", rows 51 and 57 (a). Diagnostic copy: 1,148 issues | n/a | n/a | n/a | n/a | n/a |
| NECR534_GCN_single-species (112, targeted) | Ran: project invalid (baselineValue "3 \| 54", thresholdQuantificationCycle empty (a); Excel mod_date (c)); lat/lon swapped, not caught (a) | n/a | n/a | n/a | n/a | n/a |
| Rockfish_targeted_qPCR (159, targeted) | Ran: invalid. 7 project + 156 sample errors (154 Excel date cells (c)); LOD/LOQ with intervals, free-text options (a) | n/a | n/a | n/a | n/a | n/a |

Counts at default settings (34 runs): 18 exit 0 (FAIRe-fier 8, ENA samples 5, NCBI BioSample 1,
FAIRe2QIIME 4), 15 clean stops (FAIRe-fier 1, ENA runs 5, NCBI BioSample 4, NCBI SRA 5), 1 crash
(FAIRe2QIIME on NECR534). Of the 18, one gave wrong output (FAIRe2QIIME on verte_quadeloupe) and
three wrote manifests with no file paths. FAIRe-fier: 1 of 8 validated workbooks passed (CPR_2015).
With the next form changes, NCBI BioSample reached 4 of 5 and NCBI SRA 2 of 5 (NECR534 with an
empty design_description; NOAA per assay or run). No FAIRe2ENA run step can succeed on these
examples, because none records both file names and MD5 checksums (both are Recommended in FAIRe,
required by ENA).

FAIRe-fier gave identical issue tables with checklist v1.0 and v1.0.2 for all eight workbooks it
could read (`jobs/fairefier_v1.0/`).

## Checks asked for

**checkls_ver.** All nine examples have `checkls_ver = 1` (a number, as the checklist defines it;
the checklist example is 1.2). FAIRe-fier raises no error for it. The wrapper reads it, finds no
`v1` checklist, and falls back to v1.0.2 with the note "checkls_ver is '1', which is not
available; used the latest checklist, v1.0.2." The choice is right, the wording is not (b6). The
v1.0 to v1.0.2 changes (filter_material, checksum_method options) affect none of these examples.

**Assay column layout.** Single assay in `project_level` only: CPR_2015, both NECR534 workbooks,
EirwiniBurdekin. `project_level` plus `assay1..N`: verte_quadeloupe (4), IOT-eDNA (2), NOAA (2),
AEP_Fish_sedDNA (3), Rockfish (3). `normalise_faire.py` relabelled every layout as intended. NOAA
keeps `pcr_0_1`, platform and instrument only in the assay columns; all tools handled that. The one
layout failure is a name mismatch: NECR534_GCN_metabarcoding has `assay_name` "12S-V5" in
projectMetadata D30 but "12S_V5" in sampleMetadata BS4:BS21 and experimentRunMetadata B4:B21.

**Date formats.**

| Workbook | eventDate | mod_date |
|---|---|---|
| CPR_2015 | text `2015-04-06T08:39Z` | empty |
| NECR534_GCN_metabarcoding | 17 Excel date cells, 1 "missing: not collected" (Q21) | Excel date (D16) |
| verte_quadeloupe | 22 Excel date cells | Excel date (D16) |
| IOT-eDNA | text `2021-07-06T09:25:46Z` | empty |
| noaa-aoml-gomecc4 | text `2021-09-14T11:00-04:00`; 18 "not applicable: control sample" | Excel date (D16) |
| AEP_Fish_sedDNA | text `2021-07-27` | Excel date (D16) |
| EirwiniBurdekin | 221 Excel date cells, 2 "not applicable: control sample" | empty |
| NECR534_GCN_single-species | text `2023-06-01` | Excel date (D16) |
| Rockfish_targeted_qPCR | 154 Excel date cells, 5 "not applicable: control sample" | text `2024-03` (accepted, though the checklist says yyyy-mm-dd) |

FAIRe-fier rejects every Excel date cell (c1). FAIRe2ENA and FAIRe2NCBI convert them correctly,
and convert the NOAA offsets to UTC. FAIRe2QIIME copies them as they are.

**Are FAIRe-fier's warnings sensible?** Mostly. Good: closest-option suggestions ("paired" to
"paired end", "enzumatic" to "enzymatic", "negative_control" to "negative control",
"copies/ÂµL" to "copies/µL"), the informationWithheld notes, and NOAA's 47 extra-term warnings.
Not ideal: the 5-decimal-place warning is tested on the number as stored, so trailing zeros count
against it (c7; IOT: 231 of 271 latitudes have 5 dp, 38 have 4, about the share expected from
dropped zeros); Rockfish gets 308 of these warnings although its coordinates are rounded on
purpose (informationWithheld). Missing: no range check on latitude, so the swapped coordinates in
AEP_Fish_sedDNA (latitude -110.45936) and EirwiniBurdekin (latitude 147.29) pass (c8); no
cross-sheet check of assay_name for metabarcoding, so the NECR534 mismatch passes.

## Issues

### (a) The example workbook does not follow the FAIRe checklist (or cannot meet a repository's rules)

1. **EirwiniBurdekin: duplicate samp_name.** sampleMetadata rows 51 and 57 both have
   `samp_name` "missing: not collected". samp_name is mandatory and must be unique.
   FAIRe-fier: `ERROR: Duplicate samp_name in sampleMetadata worksheet: 'missing: not collected'
   (2rows: [51, 57])`, exit 2. A diagnostic copy with the two renamed
   (`derived/EirwiniBurdekin_uniquenames.xlsx`) gave 1,148 issues: `pcr_0_1` empty (mandatory);
   `samp_category` empty for pcr_pos1 and pcr_neg1 (mandatory); 37 "negative_control" (should be
   "negative control"); probeQuencher "MGB" (D48; see c5); precip_chem_prep
   "isopropanol | sodium chloride | glycogen" (AU4:AU224; glycogen is not an option, needs
   "other: glycogen"); pcr_assay_lod_unit "copies/ÂµL" (D71, broken encoding).
2. **Latitude and longitude swapped** in three targeted workbooks. AEP_Fish_sedDNA:
   decimalLatitude -110.45936 (K4:K27), decimalLongitude "55.906799999999997" stored as text
   (J4:J27). EirwiniBurdekin: decimalLatitude 147.2372 to 148.5014 (K4 on). NECR534_GCN_single-species:
   decimalLatitude -0.92370848 (K4), decimalLongitude 54.573953 (J4), the reverse of the same sites
   in NECR534_GCN_metabarcoding. The template puts decimalLongitude (J) before decimalLatitude (K),
   which may explain it.
3. **NECR534_GCN_metabarcoding: assay_name differs between sheets** ("12S-V5" in projectMetadata
   D30, "12S_V5" in sampleMetadata and experimentRunMetadata). assay_name must match across sheets.
   Effects: FAIRe2QIIME `KeyError: '12S_V5'`; FAIRe2NCBI SRA design_description
   "Metabarcoding of NA gene NA region using PCR primers NA (NA) and NA (NA) using protocol at NA".
4. **Values that are not numbers in numeric fields.** IOT-eDNA ampliconSize "178/228" (E36);
   NOAA annealingTemp "65 | 57" (F62); NECR534_GCN_single-species baselineValue "3 | 54" (D84,
   integer field); Rockfish pcr_assay_lod "1 (0.7-1.7)" (E70:G70) and pcr_assay_loq
   "3.9 (2.8-6.5)" (E76:G76), where the interval belongs in pcr_assay_lod_LL/_UL;
   NECR534_GCN_metabarcoding tax_class_query_cutoff "6 bp difference" (D112) and size_frac_low
   "Not recorded" (AO4:AO21); NOAA size_frac_low "no pre-filter" (AQ4 on) and demux_max_mismatch
   "not provided" (D92). FAIRe-fier accepts missing values only when they start "missing" or
   "not applicable".
5. **Controlled-vocabulary values not in the list and not written as "other: ...".**
   NECR534_GCN_metabarcoding tax_assign_cat "BLAST" (D109), filter_material "Not recorded"
   (AS4:AS21); verte_quadeloupe prepped_samp_store_sol "80 mL of CL1 DNA preservation buffer
   (SPYGEN)" plus a stray "Â" and non-breaking space (AZ4:AZ25); Rockfish filter_material
   "mixed nitrocellulose" (AS4:AS162), prepped_samp_store_sol "10 mM Tris-Cl; 0.5 mM EDTA; pH 9.0"
   (AZ4:AZ162), probeQuencher "Zen/Iowa Black FQ" (D48); NOAA samp_size_unit and
   samp_vol_we_dna_ext_unit "ml" (list has "mL"; AD4 on), diss_oxygen_unit "µmol/kg" (DA4 on; list
   has mmol/kg, not µmol/kg).
6. **Mandatory value missing.** NECR534_GCN_single-species thresholdQuantificationCycle is empty
   (mandatory when assay_type is targeted and amp_vis_method is qPCR, D66).
7. **Instrument not written as the OBI label.** CPR_2015 and verte_quadeloupe "MiSeq [OBI_0002003]"
   (D80; OBI label is "Illumina MiSeq"); NECR534_GCN_metabarcoding "llumina MiSeq" (D80, typo, no
   OBI code); IOT-eDNA "Illumina NovaSeq [OBI_0003685]" (D80; NCBI needs the model, for example
   NovaSeq 6000). FAIRe2NCBI SRA stops on each: `ERROR: the instrument 'MiSeq' in the workbook is not
   one of NCBI's values. Choose the sequencing instrument on the tool form.`
8. **geo_loc_name not from the INSDC country list.** NECR534_GCN_metabarcoding "UK" (P4:P21);
   passed to ENA as "geographic location (country and/or sea)" UK and to NCBI as *geo_loc_name UK.
   Both expect "United Kingdom".
9. **lib_id not unique per library.** IOT-eDNA: the 271 COILeray rows reuse the 16SFish lib_ids
   (all 542 end "_16SFish", D4:D545). NOAA: 16S and 18S rows share lib_ids, and 7 16S controls
   sequenced in two runs keep the same lib_id with different files (for example
   RTSF_NTC_1352_S96 with RTSF_NTC_1352_S96_L001_R1 and RTSF_NTC_1543_S96_L001_R1). This blocks the
   ENA and NCBI run steps for "all assays" (expected) and for NOAA 16S, and gives repeated QIIME 2
   sample IDs.
10. **Samples that NCBI cannot register.** verte_quadeloupe: all 22 samples have the same
    coordinates (16.103, -61.841) and only 6 dates. The 13 vert01 samples fall into 6 groups that
    are identical in every sampleMetadata field except samp_name (for example SPY204182 and
    SPY210560); the other 9 differ from them only in assay_name. Not a FAIRe rule, but no form
    setting gets past NCBI's identical-attributes rule.
11. **No file names or checksums.** CPR_2015, verte_quadeloupe and IOT-eDNA have no filename or
    filename2; none of the five has checksum_filename. These are Recommended in FAIRe, so not a
    breach, but ENA needs both, so the FAIRe2ENA run step stops on all five (`ERROR: the run
    metadata needs fixing before ENA will accept it: Silk_1_01_LerayCOI: filename is empty ...`).
    A diagnostic run with invented file names and MD5s (`derived/*_withfiles.xlsx`) produced valid
    EXPERIMENT and RUN XML for every assay except NOAA 16S (item 9).
12. Smaller things: CPR_2015 samp_collect_device "Continious Plankton Recorder"; verte_quadeloupe
    filter_name "VigiDNA 0.2 Î¼M" (broken encoding of µm); verte_quadeloupe lib_layout "paired"
    (D82). AEP_Fish_sedDNA pcr_assay_lod_LL is larger than pcr_assay_lod_UL for every assay
    (1.7 > 0.7 in E73/E72), which looks like the two rows are swapped.

### (b) Wrapper code (ours)

1. **`normalise_faire.py` lines 71-84 (both copies): no check that the assay names match.** In the
   single-assay branch the copied column is named after projectMetadata's assay_name ("12S-V5"),
   and nothing checks it against experimentRunMetadata ("12S_V5"). Result: FAIRe2QIIME ends with a
   bare traceback (`KeyError: '12S_V5'`, `jobs/faire2qiime_lib_id/NECR534_GCN_metabarcoding/stderr.txt`),
   although the README says missing columns get a plain message; FAIRe2NCBI SRA exits 0 with
   design_description "NA" in all 18 rows (`jobs/faire2ncbi_sra_form/NECR534_GCN_metabarcoding_all/`).
   A check that every experimentRunMetadata assay_name has a projectMetadata column would catch both.
2. **FAIRe2QIIME: no guard against output names that collide** (`faire2qiime.xml` command).
   Upstream names metadata files `{project_id}_{gene}-{subfragment}` (`faire2qiime.py` line 95).
   verte_quadeloupe's four assays are all "12S rRNA" with no subfragment, so
   `verte_quadeloupe_12S_metadata.tsv` was written four times and only cetac (4 of 22 rows) is left.
   The log shows "Generated metadata file verte_quadeloupe_12S_metadata.tsv" four times; the job
   exits 0. The cause is upstream (c), but the wrapper could stop or name files by assay_name.
3. **FAIRe2QIIME: manifests written when there are no file names.** With manifests on (the
   default), CPR_2015 (53 rows), IOT-eDNA (542) and verte_quadeloupe (22) get manifests in which
   every path is `/path/to/sequences/<seq_run_id>/nan` (upstream `str(x)`, `faire2qiime.py` lines
   102-103). The wrapper gives no warning.
4. **`faire2ena_galaxy.py` lines 107-110: wrong count of converted dates.** For a column pandas
   reads as datetime64 (verte_quadeloupe), `astype(str)` already gives "2021-06-06", so the log
   says `INFO: converted 0 eventDate value(s)` although all 22 were converted (without conversion
   upstream writes "not provided" for all 22: `jobs/faire2ena_sample/verte_quadeloupe_nodateconv/`).
   Output correct, log wrong.
5. **`faire2ena_galaxy.py` lines 188-200: the lib_id advice is hidden.** The repeated-lib_id
   problem is added after the per-row file and checksum problems, and the list is cut at 20, so for
   IOT-eDNA and NOAA the message ends "... and 1065 more" / "... and 1997 more" and never shows
   "Run the tool once per assay".
6. **`fairefier_cli.py` lines 390-395: misleading checklist note.** `checkls_ver = 1`, the form all
   nine examples use and the README recommends, is reported as "checkls_ver is '1', which is not
   available; used the latest checklist, v1.0.2." It could map a bare major version to the latest
   matching checklist and say so.
7. **FAIRe2ENA runs: no way past a lib_id repeated within one assay.** NOAA 16S stops with
   `these lib_id values appear more than once within the assay: RTSF_NTC_1352_S96, ...` and no
   advice (line 197). The tool has no seq_run_id filter or suffix, which FAIRe2NCBI SRA has (by
   seq_run the same data gave 311 + 197 valid rows).
8. **`faire2ena_run.xml` line 65: "Add the assay name" is on by default**, which doubles the name
   when lib_id already ends with it (Silk_1_01_LerayCOI_LerayCOI, SPY204198_vert01_vert01,
   FK1170 B2-027-12S_Riaz_12S_V5_12S_V5). Cosmetic.

No crash came from wrapper code itself. The wrapper stops in FAIRe2ENA and FAIRe2NCBI were clear
and pointed to the right fields in every case except b1, b5 and b7.

### (c) Upstream scripts and checklist

FAIRe-fier (`create_validator.py`):

1. **Excel date cells always fail** (`check_datetime`, line 172 `v = str(v)` gives
   "2024-05-04 00:00:00"). Hits mod_date in 5 workbooks and eventDate in 4 (17 + 22 + 221 + 154
   samples). Already listed as upstream issue 4 in the FAIRe-fier README.
2. **Decimal numbers stored as text fail.** `convert_str2numeric` sends any string with a "." into
   the range branch (line 65), so "1.1" and "-5.2" give "Require value to be numerics or range
   MIN-MAX." Checked directly: "1.1", "1.1000000000000001", "-5.2" fail; "12", "3-54", "2e3" pass.
   Evidence: AEP_Fish_sedDNA pcr_assay_lod_LL "1.1000000000000001" (G73) and pcr_assay_loq_LL
   "4.9000000000000004" (F79). In sampleMetadata pandas usually turns such text into numbers first,
   so this mostly bites in projectMetadata, where assay columns mix text and numbers. Not in the
   README's upstream list.
3. **Misleading message for text containing "e".** Line 55 treats any value containing "e" as
   scientific notation: "6 bp difference" and "no pre-filter" give "Require scientific notation to
   be in format '3x10+8' or '3e8'."
4. Fuzzy matching is case-sensitive in effect: "ml" is "Option not found" rather than a suggestion
   of "mL" (difflib ratio 0.5, cutoff 0.7).
5. **Checklist v1.0.2 inconsistencies:** probeQuencher's example is "MGB" but the options list
   "Minor Groove Binder (MGB)", so the checklist's own example fails (EirwiniBurdekin D48); the
   option "lowa Black" is a typo for "Iowa Black".
6. `check_duration` rejects "P0.5D" (EirwiniBurdekin BA4:BA224), which ISO 8601 allows (a decimal
   in the smallest unit). Debatable; "PT12H" would pass.
7. The 5-decimal-place check works on the stored number (line 144), so 5-dp values ending in 0 are
   flagged (IOT-eDNA, 89 warnings).
8. No range check on decimalLatitude and decimalLongitude (a2 passes validation).
9. No assay_name cross-check between sheets for metabarcoding (`check_assayname` runs only for
   targeted assays).

FAIRe2ENA (`faire2ena_sample.py`):

10. `'amount or size of sample collected'` always gets UNITS L (line 110), so the XML says
    "1920 ml" in L (NOAA) and "5 other:nautical miles" in L (CPR_2015).
11. Mandatory depth defaults to "0" (line 23, "most OceanOmics samples are surface"), applied
    without a stop to all 18 NECR534 and all 22 verte_quadeloupe samples (logged as WARNING).
12. FAIRe missing values are not mapped to ENA's: eventDate "missing: not collected" (NECR534 Q21)
    and "not applicable: control sample" (18 NOAA controls) become "not provided"; ENA has
    "not collected" and "missing: control sample". "not applicable: control sample" is passed
    unchanged into other ENA attributes for NOAA controls, including "nucleic acid extraction"
    "not applicable: control sample (ZymoBIOMICS 96 MagBead DNA Kit )".
13. Dissolved oxygen, DIC, nitrate and nitrite go out twice, as "dissolved oxygen" (no unit) and
    "dissolved_oxygen" (with unit) (IOT-eDNA, NOAA). samp_vol_we_dna_ext twice as well (known).

FAIRe2NCBI (`scripts/FAIRe2BioSample.py`, `scripts/FAIRe2SRA.py`):

14. **lat_lon rounded to 3 decimal places** (`FAIRe2BioSample.py` lines 1551-1559). IOT-eDNA's 262
    distinct coordinate pairs become 166 lat_lon values; CPR_2015 -43.3185655 becomes 43.319 S.
15. *depth is read from maximumDepthInMeters only (`FAIRe2BioSample.py` line 2273; mirrored in
    `faire2ncbi_galaxy.py` line 80), so CPR_2015, which has only minimumDepthInMeters = 10, is
    reported as having no depth.
16. The "fields with 100% unique values" list includes filter_passive_active_0_1 (a 0/1 field) for
    NOAA; the wrapper passes this list on as advice.
17. The SRA title for controls reads "... metabarcoding of metagenome in not applicable: control
    sample" (NOAA).
18. FAIRe "other:" units pass through: samp_size "5 other:nautical miles" (CPR_2015).

FAIRe2QIIME (`faire2qiime.py`):

19. Output names are built from gene and subfragment, not assay_name, so assays on the same gene
    overwrite each other (b2). Empty file names become "nan" in manifests (b3). Repeated sample IDs
    only give "Warning: Duplicated entries found in column 'lib_id' for assay 'ssu16sv4v5-emp'"
    (NOAA); QIIME 2 needs unique IDs.

## Not run, and limits

- FAIRe2QIIME does not read OTU or taxa tables (it uses projectMetadata, sampleMetadata and
  experimentRunMetadata only), so neither the otuFinal/taxaFinal sheets nor the separate files in
  IOT-eDNA/ and noaa-aoml-gomecc4/ were used. Nothing was skipped for this reason.
- FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME were not run on the four targeted-assay workbooks (none has
  experimentRunMetadata).
- FAIRe2ENA runs used stand-in receipts; nothing was checked against ENA or NCBI validators, so
  whether they accept "not applicable: control sample", "missing: not collected", aliases with
  spaces (NECR534) and the units above is unknown.
- The FAIRe-fier outputs were not compared with the hosted Shiny app for these workbooks.
- openpyxl prints "Data Validation extension is not supported and will be removed" to stderr for
  most workbooks; harmless with `detect_errors="exit_code"`.

## Files

- `scripts/`: run scripts (`run_fairefier.sh`, `run_ena_sample.sh`, `run_ncbi.sh`, `run_qiime.sh`)
  and checkers.
- `jobs/<tool>[_<variant>]/<workbook>/`: inputs (symlinks), outputs, `log.txt`, `stderr.txt`.
- `derived/`: edited copies used for diagnostic runs only.
