# Wrapped tools on the FAIRe example workbooks

An integration test of FAIRe-fier, FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME on the nine example
workbooks published on the FAIR-eDNA website
([FAIR-eDNA.github.io/docs/examples](https://github.com/FAIR-eDNA/FAIR-eDNA.github.io/tree/main/docs/examples)):
five metabarcoding and four targeted-assay workbooks. The examples have no stated licence, so
they are not stored here.

`RESULTS.md` has the full results: a table of workbook by tool, then every issue with its evidence,
grouped as (a) the workbook does not follow FAIRe, (b) our wrapper code, (c) the upstream scripts.
The scripts in `scripts/` take their folders from the environment: `EXAMPLES_RUN` (a working
folder holding a copy of `tools/`), `FAIRE_EXAMPLES` (`docs/examples` in a copy of the FAIR-eDNA
website repository) and, optionally, `PYTHON`.

In short, at the form defaults: FAIRe-fier validated 8 of 9 workbooks and passed one (CPR_2015);
FAIRe2ENA made samples for all five metabarcoding workbooks, but no run step can succeed, because
none records both file names and MD5 checksums; FAIRe2NCBI made BioSample tables for 4 of 5 and SRA
tables for 2 of 5 after form changes; FAIRe2QIIME finished on 4 of 5, one with lost rows.

## Fixed after this run (wrapper code, issues b1 to b8)

| Issue | Fix |
|---|---|
| b1 assay_name spelt differently between sheets (`12S-V5`, `12S_V5`) gave a `KeyError` in FAIRe2QIIME and empty design descriptions in FAIRe2NCBI | `normalise_faire.py` (both copies) matches names that differ only in punctuation or case, with a warning, and stops with a plain message otherwise |
| b2 FAIRe2QIIME assays on the same gene and subfragment overwrite each other | the tool stops and says why |
| b3 FAIRe2QIIME manifests with paths ending in `nan` | with manifests on, runs without a file name stop the tool |
| b4 FAIRe2ENA logged "converted 0 eventDate" for Excel date cells | counts them |
| b5 FAIRe2ENA lib_id advice hidden below a long list | listed first |
| b6 FAIRe-fier called `checkls_ver = 1` "not available" | uses the latest v1 checklist and says so |
| b7 FAIRe2ENA lib_id repeated within an assay had no advice | the message says each run needs its own lib_id (no run filter yet) |
| b8 FAIRe2ENA doubled the assay suffix (`..._LerayCOI_LerayCOI`) | not added when every lib_id already ends with it |

## Still to do

- Report the upstream issues (c) to the FAIRe-fier, FAIRe2ENA, FAIRe2NCBI and FAIRe2QIIME authors,
  and the workbook issues (a) to the FAIRe authors, who publish the examples. Drafts were ready on
  5 November 2026 in the Claude Doc "FAIRe upstream issue drafts"; they add two primer errors found
  since: IOT-eDNA gives the Illumina P7 adapter as its 16S reverse primer, and verte_quadeloupe's
  tele01 reverse primer lacks three bases of teleo_R.
- ~~Add a sequencing-run filter to the FAIRe2ENA run tool, as FAIRe2NCBI SRA has.~~ Done 5 November
  2026.
