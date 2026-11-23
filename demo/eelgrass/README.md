# Nova Scotia eelgrass demonstration set

Published files from a COI metabarcoding study of invertebrates in eelgrass (*Zostera marina*)
meadows across Nova Scotia, used to show the FAIRe tools on a minimal metabarcoding dataset. The
published files give a table of reads per species and sample, plus the coordinates of each site. They
have no sample table, no controls and no sequence linked to each species. That is still enough for a
FAIRe workbook that passes FAIRe-fier, and for a Darwin Core archive of presence records for GBIF.

## Source and licence

Data from: Applying eDNA metabarcoding to assess invertebrate biodiversity of eelgrass (*Zostera
marina*) meadows across Nova Scotia (2025). Dryad,
[doi:10.5061/dryad.gqnk98t0c](https://doi.org/10.5061/dryad.gqnk98t0c), version of 7 November 2025.
Project led by Courtney Trask (Cape Breton University); corresponding author Nick Jeffery (Fisheries
and Oceans Canada, Bedford Institute of Oceanography). Released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), as is all data on Dryad. Raw reads:
NCBI BioProject PRJNA1145319.

**Changes made:**
- The Dryad README is renamed `Dryad_README.md`, so it doesn't clash with this file.
- The two FASTA files (8 MB) and `comp_data_raw.csv` (the comparison with other survey methods) are left out.
- The two tables are as published.

## Files

| File | What it holds |
|---|---|
| `Final_ASVTable_withTaxonomy_Filtered.csv` | Reads per species and sample. Each row has a phylum, class and species (with underscores; two are named only to the genus, with a BOLD BIN) and the RDP classifier's probability. Then come 50 sample columns, named by site and replicate (CAB-1, CAB-2 ...) |
| `Site_coordinates.csv` | The 17 sites: name, latitude, longitude (WGS84) and code |
| `Dryad_README.md` | The Dryad README: the files, the dates, the primers and the pipeline. Used as the data dictionary |

## Running it

From the top of the repository:

```
bash dev/faire_mapper_eelgrass/run.sh OUTDIR
```

It runs each step as a person would in Galaxy or the Shiny app:

1. **Make the sample table** (`prepare_table.py`). The study published none, so a person following
   the guide makes one from the ASV table's column names and the site coordinates. It has one row per
   sample with:
   - the site, its code and the replicate;
   - the site's coordinates;
   - the period of sampling as an ISO 8601 interval: 2019-07/2019-09 for the ten mainland sites and
     2023-06/2023-10 for the seven sites of 2023, as the Dryad page gives them;
   - the country and province;
   - Category (all samples);
   - ENVO terms: marine biome, sea grass bed and coastal sea water.

   `make_taxa.py` makes the taxon table for FAIRe to Darwin Core: each name with kingdom Animalia
   and the authors' phylum and class.
2. **Propose mapping**, with the Dryad README as the data dictionary, then the reviewer's decision
   (`reviewer_decisions.tsv`). The one row for review is *Replicate*, which the review keeps as the
   authors' own column, as FAIRe's biological_rep is the number of replicates for the project.
3. **Apply mapping**, with the species table as otuFinal and taxaFinal, and the project values
   (`project_values.tsv`): primers, target gene, pipeline, reference database, licence and citation.
4. **FAIRe-fier** checks the workbook.
5. **FAIRe to Darwin Core** writes the archive for GBIF.

## What you should see

- Propose mapping accepts 11 of the 13 columns. *Replicate* goes for review, and *Site code* gets no
  term.
- Apply mapping writes 50 samples, and otuFinal and taxaFinal with 138 taxa. Each taxon's seq_id is
  its name, as the reads are summed per taxon. Two lists say what is still missing:
  - **Mandatory terms with no value:** seq_run_id, as the published files don't say which samples
    were sequenced in which run.
  - **Warnings:** dna_sequence (mandatory in taxaFinal) is empty for all 138 taxa.
- FAIRe-fier: *Success* for projectMetadata and sampleMetadata. It warns about coordinates with
  fewer than five decimal places, and about the two columns kept as the authors' own (Site code and
  Replicate).
- FAIRe to Darwin Core writes 869 presence records of 138 taxa: 491 from 2019 and 378 from 2023.
  Two taxa are named to the genus (*Clitellio*, *Boonea*), with the authors' label (including its
  BOLD BIN) in verbatimIdentification.

The archive is for demonstration. It has not been published to GBIF, as the data belong to the
authors.

## Things to know about these data

- **No sequences behind the names.** The ASV table sums the reads of each species. The FASTA files
  on Dryad hold every ASV, but nothing links an ASV to a species. So the records can't carry the
  sequence that identified them, and the identifications can't be checked or redone from the
  records. That is the main gap in this dataset, and why it shows the minimum. The authors' per-ASV
  tables would close it; we have asked the authors whether they can be shared under an open licence.
- **No sample dates.** Each record gets the period in which its site was sampled. The Dryad README
  says the Cape Breton sites were sampled between June and August 2023, and its methods say June to
  October for the seven sites of 2023 (one, Chebogue, is on the south shore). The demonstration uses
  the wider period.
- **Site coordinates.** Each replicate takes its site's coordinates. dataGeneralizations says so.
- **What was sampled.** The 2019 samples were water samples (He et al. 2022, the fish study the
  2019 sites came from). The Dryad files don't say for 2023, so the same is assumed.
- **Primers.** The Dryad README names "the Leray et al. (2013) primer set". The bundled primer table
  has six pairs under that citation. The authors' published pipeline trims mlCOIintF and jgHCO2198,
  so the project values give that pair.
- **Wreck Cove** is WRK in the coordinates and WRK02 in the ASV table (a second visit in 2019).
- **No controls** are in the published table, so none could be described or left out.
- **Rose Bay** has two replicates; every other site has three.
