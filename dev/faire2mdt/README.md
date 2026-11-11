# FAIRe2MDT on the FAIRe example workbooks

The Galaxy driver (`tools/faire2mdt/faire2mdt_galaxy.R`) and upstream `FAIRe2MDT.R` run by hand
(`run_by_hand.R`: the user section filled in as the script's comments describe, then the upstream
code) on the FAIRe metabarcoding examples
([FAIR-eDNA.github.io/docs/examples/metabarcoding](https://github.com/FAIR-eDNA/FAIR-eDNA.github.io/tree/main/docs/examples/metabarcoding)),
3 November 2026. The examples have no stated licence, so they are not stored here.

```bash
bash run_examples.sh EXAMPLES_DIR OUT_DIR Rscript
python -I compare.py OUT_DIR
```

`make_test_data.py` writes the Galaxy tool's test data. `make_target_gene_table.py` writes
`tools/faire2mdt/mdt_target_gene.tsv` from MDT's bundled copy of the GBIF target_gene vocabulary
and the FAIRe checklist.

## Results

All 11 assay and run combinations with otuFinal and taxaFinal tables converted in Galaxy; 5
converted by hand. noaa-aoml-gomecc4 has no otuFinal tables, so it could not be tried.

| Workbook | Assay / run | By hand | Galaxy | Log notes and warnings |
|---|---|---|---|---|
| IOT-eDNA | COILeray, 16SFish / Library_2021, Library_2022 (4) | ran | ran | 16SFish: target_gene written as the GBIF term |
| CPR_2015 | LerayCOI / seq_run_1 | ran | ran | none |
| NECR534_GCN_metabarcoding | 12S-V5 / Run1 | stops (assay spelt 12S_V5 in experimentRunMetadata) | ran | used 12S_V5; target_gene written as the GBIF term; 1161 empty OTU table cells written as 0 |
| verte_quadeloupe | cetac, mamm01, tele01, vert01 (2 runs) (5) | stops (no seq_id header in the OTU sheets) | ran | first column taken as seq_id; target_gene written as the GBIF term; empty cells written as 0 (cetac 25, mamm01 16); mamm01 column SPY224104_M is empty and not a sample of the run |

Where both ran, the OTU_table sheets are identical, and the Study sheets differ only in target_gene
for IOT-eDNA 16SFish (16S rRNA (LSU mitochondria) by hand, LSU_rRNA_16S_mitochondrial in
Galaxy). In the Samples and Taxonomy sheets, the only differences are numbers written with Excel's 17 digits by hand and the digits Excel shows
in Galaxy (CPR_2015 148 cells, IOT-eDNA 42 to 1405 cells per sheet; for example
105.70851999999999 and 105.70852). None of these five has Excel date cells. NECR534 does: by hand,
with the assay spelt as in experimentRunMetadata (12S_V5), eventDate 2023-06-01 comes out as 45078
and mod_date as 45416; in Galaxy as 2023-06-01 and 2024-05-04.

## Workbook issues to report to the FAIRe authors

- verte_quadeloupe: the otuFinal sheets have an empty top-left cell where FAIRe has seq_id; vert01
  OTU and taxonomy IDs start with `>` (left from a FASTA file); otuFinal_mamm01_mamm has a column
  with no counts (SPY224104_M) for a sample that is not in the metadata; blank cells where a read
  count of 0 is meant.
- NECR534: assay_name 12S-V5 in projectMetadata and 12S_V5 in experimentRunMetadata (already
  reported for the other tools); eventDate cells copied into verbatimEventTime; blank OTU cells.
- noaa-aoml-gomecc4: no otuFinal tables, so no MDT workbook can be made from the example as
  published.
