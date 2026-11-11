# normalise_faire.py differential check (2026-11-09)

| Case | Copy or tool | What differs | First differences (expected -> normalised) | Status |
|---|---|---|---|---|
| L01_faire_twin | upstream FAIRe2QIIME | 5 output files identical | | same |
| L02_faire_twin_spelling | faire2qiime | projectMetadata: 1 cells differ (openpyxl), 1 differ (pandas literal) | F30: 'ssu18sv9-emp' (str/s) -> 'SSU18Sv9_EMP' (str/s) | allowed: the test input spells assay2 SSU18Sv9_EMP in projectMetadata; the header is corrected (with a warning), the assay_name row keeps the input |
| L02_faire_twin_spelling | faire2qiime | log | WARNING: assay_name 'ssu18sv9-emp' in experimentRunMetadata is written 'SSU18Sv9_EMP' in projectMetadata; using 'ssu18sv9-emp'. Correct the workbook so the names match. | note |
| L02_faire_twin_spelling | upstream FAIRe2QIIME | exit 0 vs 0; files differ: noaa-aoml-gomecc4_18S-V9_metadata.tsv |  | allowed: the same assay_name row reaches the assay_name_PROJECT column of the 18S metadata table |
| L02_faire_twin_spelling | faire2ncbi+edna2obis | projectMetadata: 1 cells differ (openpyxl), 1 differ (pandas literal) | F30: 'ssu18sv9-emp' (str/s) -> 'SSU18Sv9_EMP' (str/s) | allowed: the test input spells assay2 SSU18Sv9_EMP in projectMetadata; the header is corrected (with a warning), the assay_name row keeps the input |
| L02_faire_twin_spelling | faire2ncbi+edna2obis | log | WARNING: assay_name 'ssu18sv9-emp' in experimentRunMetadata is written 'SSU18Sv9_EMP' in projectMetadata; using 'ssu18sv9-emp'. Correct the workbook so the names match. | note |
| L03_single_assay | faire2qiime | projectMetadata: 120 cells differ (openpyxl), shape differs (pandas literal) | E1: empty () -> 'ssu16sv4v5-emp' (str/s); E2: empty () -> 'Luke Thompson' (str/s); E3: empty () -> 'https://orcid.org/0000-0002-3911-1280' (str/s); E4: empty () -> 'Luke Thompson' (str/s) (+116 more) | allowed: single-assay layout: project_level copied into a new column headed by the assay_name |
| L03_single_assay | upstream FAIRe2QIIME | exit 1 vs 0; files differ: 20220613_Amplicon_PE250_16S-V4V5_manifest.tsv, 20220831_16S-Amplicon_PE250_16S-V4V5_manifest.tsv, noaa-aoml-gomecc4_16S-V4V5_metadata.tsv | KeyError: 'ssu16sv4v5-emp' | allowed: upstream cannot read the single-assay layout (KeyError on the assay name); converting it is what normalise_faire.py is for |
| L03_single_assay | faire2ncbi+edna2obis | projectMetadata: 120 cells differ (openpyxl), shape differs (pandas literal) | E1: empty () -> 'ssu16sv4v5-emp' (str/s); E2: empty () -> 'Luke Thompson' (str/s); E3: empty () -> 'https://orcid.org/0000-0002-3911-1280' (str/s); E4: empty () -> 'Luke Thompson' (str/s) (+116 more) | allowed: single-assay layout: project_level copied into a new column headed by the assay_name |
| N01_associated_sequences_na | upstream FAIRe2QIIME | not comparable: upstream fails on both | KeyError: 'seq_run_id' | not run |
| P00_ncbi_noaa_fixture | upstream FAIRe2QIIME | not comparable: upstream fails on both | KeyError: 'seq_run_id' | not run |
| P01_noaa_layout | upstream FAIRe2QIIME | 5 output files identical | | same |
| P02_noaa_with_analysis_sheets | upstream FAIRe2QIIME | not comparable: upstream fails on both | KeyError: 'seq_run_id' | not run |
| P03_na_like_text | upstream FAIRe2QIIME | 5 output files identical | | same |
| P04_text_starting_with_equals | upstream FAIRe2QIIME | 5 output files identical | | same |
| P05_escaped_control_character | upstream FAIRe2QIIME | 5 output files identical | | same |
| P06_dates_and_times | faire2qiime | sampleMetadata: 1 cells differ (openpyxl), 0 differ (pandas literal) | FB6: datetime.time(10, 23) (time/d) -> '10:23:00' (str/s) | allowed: pandas reads an Excel time cell as a time, which is written back as text (10:23:00); pandas reads the same text from both, and no tool output changes (results/DOWNSTREAM_NCBI.md, upstream FAIRe2QIIME row) |
| P06_dates_and_times | upstream FAIRe2QIIME | 5 output files identical | | same |
| P06_dates_and_times | faire2ncbi+edna2obis | sampleMetadata: 1 cells differ (openpyxl), 0 differ (pandas literal) | FB6: datetime.time(10, 23) (time/d) -> '10:23:00' (str/s) | allowed: pandas reads an Excel time cell as a time, which is written back as text (10:23:00); pandas reads the same text from both, and no tool output changes (results/DOWNSTREAM_NCBI.md, upstream FAIRe2QIIME row) |
| P07_numbers_and_ids | upstream FAIRe2QIIME | 5 output files identical | | same |
| P08_whitespace | upstream FAIRe2QIIME | 5 output files identical | | same |

## Published FAIRe example workbooks

Each normalised copy compared with its input, as FAIRe2NCBI's driver reads it (pandas, literal text). projectMetadata headers are meant to change; every other cell is meant to stay as it was. Counts only; no cell values are shown, as the examples carry no stated licence.

| Workbook | Copy | Result | projectMetadata cells changed | other sheets: cells changed |
|---|---|---|---|---|
| CPR_2015.xlsx | faire2qiime | exit 0 | shape (121, 4)->(121, 5) | none |
| CPR_2015.xlsx | faire2ncbi+edna2obis | exit 0 | shape (121, 4)->(121, 5) | none |
| IOT-eDNA.xlsx | faire2qiime | exit 0 | 2 | none |
| IOT-eDNA.xlsx | faire2ncbi+edna2obis | exit 0 | 2 | none |
| NECR534_GCN_metabarcoding.xlsx | faire2qiime | exit 0 | shape (121, 4)->(121, 5) | none |
| NECR534_GCN_metabarcoding.xlsx | faire2ncbi+edna2obis | exit 0 | shape (121, 4)->(121, 5) | none |
| noaa-aoml-gomecc4.xlsx | faire2qiime | exit 0 | 2 | none |
| noaa-aoml-gomecc4.xlsx | faire2ncbi+edna2obis | exit 0 | 2 | none |
| verte_quadeloupe.xlsx | faire2qiime | exit 0 | 4 | none |
| verte_quadeloupe.xlsx | faire2ncbi+edna2obis | exit 0 | 4 | none |
| AEP_Fish_sedDNA.xlsx | faire2qiime | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| AEP_Fish_sedDNA.xlsx | faire2ncbi+edna2obis | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| EirwiniBurdekin.xlsx | faire2qiime | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| EirwiniBurdekin.xlsx | faire2ncbi+edna2obis | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| NECR534_GCN_single-species.xlsx | faire2qiime | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| NECR534_GCN_single-species.xlsx | faire2ncbi+edna2obis | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| Rockfish_targeted_qPCR.xlsx | faire2qiime | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |
| Rockfish_targeted_qPCR.xlsx | faire2ncbi+edna2obis | exit 1: ERROR: the workbook has no 'experimentRunMetadata' sheet. | | |

Unexpected differences: 0
