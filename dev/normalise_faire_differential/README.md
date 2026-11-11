# normalise_faire.py differential check

`normalise_faire.py` rewrites FAIRe-ator workbooks in the FAIRe-NOAA layout before FAIRe2QIIME, FAIRe2NCBI and edna2obis read them. It is meant to change only two things: the projectMetadata assay headers, and (for single-assay workbooks) a copy of the project_level column. These scripts check that every other cell, and every tool output, stays the same.

Each named case lists the differences it is meant to make, and any other difference fails the check. The downstream comparison runs each tool twice, once after `normalise_faire.py` and once with the workbook as written.

## Running it

```
bash dev/normalise_faire_differential/run_all.sh [folder of published FAIRe example workbooks]
```

It needs the Python packages the three tools list in their `macros.xml` (FAIRe2QIIME also needs `pyfiglet`). The edna2obis runs are offline: the taxonomy comes from the tool's own test mapping table. The example workbooks are optional and are not stored here, because they carry no stated licence; the report shows only counts for them, never cell values.

| Script | What it does |
|---|---|
| `make_cases.py` | Writes the cases (below) from workbooks in the tools' `test-data` folders |
| `check.py` | Runs both copies of `normalise_faire.py` on each case, compares every cell (as openpyxl and as FAIRe2NCBI's driver read them), and runs upstream FAIRe2QIIME on the expected and normalised workbooks. Writes `results/RESULTS.md`; exits 1 on any difference not in `ALLOWED` |
| `downstream.py` | Runs the FAIRe2NCBI and edna2obis Galaxy drivers twice on NOAA-layout workbooks: as written, and with `normalise_faire.normalise` replaced by a plain copy (`run_driver.py`). Normalising such a workbook is meant to change nothing, so any difference in the outputs comes from `normalise_faire.py` |
| `run_all.sh` | Rebuilds the cases and runs everything |

## Cases

| Case | Built from | What it tests |
|---|---|---|
| P00 | FAIRe2NCBI's NOAA-layout test workbook | Pass-through (it has no seq_run_id, so upstream FAIRe2QIIME cannot read it) |
| P01 | FAIRe2QIIME's two-assay test workbook, relabelled into the NOAA layout | Pass-through; upstream FAIRe2QIIME accepts it |
| P02 | edna2obis's workbook with analysisMetadata sheets | Pass-through of extra sheets |
| P03 to P08 | P01 with awkward values in fields the tools carry into their outputs | NA-like text, text starting with `=`, an escaped control character, dates and times, numbers and IDs, whitespace |
| N01 | P00 with associatedSequences `NA` and `N/A` in two runs | FAIRe2NCBI's "only runs not yet submitted" option |
| L01, L02 | P01 in the FAIRe-ator layout (L02 with a different spelling of one assay_name) | Normalising should give back P01 |
| L03 | A single-assay workbook | The project_level conversion |

## Findings, 9 November 2026 (before the fix)

Workbooks already in the NOAA layout (P01, P02) came out unchanged, and the intended conversions (L01 to L03) behaved as designed. Three kinds of value changed:

1. **NA-like text becomes an empty cell.** `NA`, `N/A`, `null`, `nan`, `None`, `#N/A`, `n/a` and `NULL` are blanked in every sheet, because the script reads with pandas' default missing-value list. The published NECR534 metabarcoding workbook loses 145 sampleMetadata cells this way.
   - FAIRe2NCBI, "only runs not yet submitted": runs marked `NA` or `N/A` in associatedSequences are treated as new (10 runs instead of 8, and 5 BioSamples instead of 3). Upstream FAIRe2BioSample deliberately treats literal NA and N/A there as not blank (`_associated_sequences_is_blank`), and both upstream scripts read experimentRunMetadata with `keep_default_na=False`.
   - FAIRe2NCBI BioSample: `NA` in a mandatory field gets the fill value chosen on the form. Without normalising, the driver's own check sees `NA` as a value and upstream then writes `not collected` without saying so. A fix to the normaliser alone would therefore bring in that silent change.
   - FAIRe2QIIME: no change (upstream reads with pandas' defaults anyway).
   - edna2obis: no change, because the driver's own `prepare_workbook` reads with pandas' defaults and blanks the same values. Upstream edna2obis reads with `na_values=[""], keep_default_na=False`, so on its own it would keep the text (not yet run directly).
2. **Text starting with `=` becomes an empty cell**, because openpyxl writes it as a formula. FAIRe2QIIME's metadata tables change. FAIRe2NCBI's and edna2obis's drivers lose these values even without normalising, because they rewrite the workbook the same way; in edna2obis the occurrence table then had no locationID for any event.
3. **Excel time cells become text** (`10:23:00`). Pandas reads the same text either way, and no tool output changed.

## Fix, 9 November 2026

Failing tool tests came first, each built by `make_testdata.py`: FAIRe2NCBI SRA and BioSample with "only runs not yet submitted" and `NA` or `N/A` in associatedSequences, `=see notes` in a BioSample field, and `=see notes` in FAIRe2QIIME's metadata tables. A fourth test (`NA` in a mandatory field stops the default 'stop') passed before the fix and guards against the silent `not collected`.

- `normalise_faire.py` (all three copies) reads only empty cells as empty and saves all text as text. Saving text as text also covers `#N/A`, which openpyxl would otherwise save as an Excel error cell that pandas reads as empty; `check.py` now compares each cell's Excel type, which is how this showed up after the first fix. `--check_filled` (FAIRe2QIIME's filename check) still treats text such as `NA` as empty, as upstream FAIRe2QIIME reads it.
- The FAIRe2NCBI driver reads each sheet as upstream does: text such as `NA` is empty in sampleMetadata and projectMetadata (the log counts these cells), and a value in experimentRunMetadata. It saves its prepared workbook with the same function as `normalise_faire.py`.
- edna2obis's `prepare_workbook` (decided 9 November: match upstream) reads cells as upstream edna2obis does (`na_values=[""], keep_default_na=False`), saves with the same function, and counts NA-like text in the log. Its test workbook has `=Sta1` and `N/A` in station_id, which now reach locationID; before, locationID was missing from the occurrence core. Upstream itself drops NA-like text in some other fields later in its pipeline (env_medium in the DNA-derived extension, for example). `downstream.py` still finds edna2obis identical with and without normalising, as both runs go through `prepare_workbook`.
- Time cells are left as they are (allowed in `check.py`).

After the fix, `check.py` finds no unexpected differences, the published examples change only in projectMetadata, and every downstream comparison is identical.
