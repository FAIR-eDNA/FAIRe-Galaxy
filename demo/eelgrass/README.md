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
    were sequenced in which run (the version with sequences gives each year's table its own label).
  - **Warnings:** dna_sequence (mandatory in taxaFinal) is empty for all 138 taxa.
- FAIRe-fier: *Success* for projectMetadata and sampleMetadata. It warns about coordinates with
  fewer than five decimal places, and about the two columns kept as the authors' own (Site code and
  Replicate).
- FAIRe to Darwin Core writes 869 presence records of 138 taxa: 491 from 2019 and 378 from 2023.
  Two taxa are named to the genus (*Clitellio*, *Boonea*), with the authors' label (including its
  BOLD BIN) in verbatimIdentification.

The archive is for demonstration. It has not been published to GBIF, as the data belong to the
authors.

## With the sequences

The authors' GitHub repository
([dfo-mar-mpas/coastal-invertebrate-metabarcoding](https://github.com/dfo-mar-mpas/coastal-invertebrate-metabarcoding))
holds what the Dryad files lack: reads per ASV, each ASV's classification and sequence, the
controls, the date of each 2019 site visit, and a key to the 2023 samples. Nick Jeffery agreed on 24
November 2026 that we can use them, and is adding a licence to the repository. Until it is there,
this repository holds no copies: `fetch_github.sh` downloads the files at a fixed commit and checks
each one.

```
bash dev/faire_mapper_eelgrass/run_asvs.sh OUTDIR
```

1. `prepare_asvs.py` keeps the ASVs the authors' code keeps (an RDP species probability above
   0.90, in `code/R/01a_Merge_taxonomy_andASVs.R`) whose species is in the published table and
   that have reads in a published sample. It writes one table and one FASTA file for each year.
2. `prepare_table.py` makes the sample table as before, now with the 23 controls and the date of
   each 2019 site visit. The 2023 samples keep the period of sampling.
3. Apply mapping writes each year's table as its own sheet (otuFinal_LerayCOI_COI_2019 and
   otuFinal_LerayCOI_COI_2023), with a sequence for every ASV. The two years were processed
   separately, so each is treated as its own sequencing batch. COI_2019 and COI_2023 are our labels,
   not run IDs from the sequencer.
4. FAIRe to Darwin Core writes one presence record per sample and ASV, each with its sequence.

What you should see:

- 416 ASVs of 134 species: 222 ASVs from 2019 and 194 from 2023. Four published names have no ASV
  behind them (*Elysia catulus*, *Leitoscoloplos acutus*, *Lepidonotus squamatus* and
  *Speziorchestia grillus*). The authors probably named these after classification.
- 27 of the 6,900 sample and species cells differ from the published table (`differences.tsv`), from
  the authors' curation after classification. Two look like swapped columns: *Cancer borealis* in
  TAW-1 and TAW-3, and *Ameritella agilis* in ESB-2 and ESB-3.
- 23 controls: in 2019, a field control at each site, a lab control (CON-LC) and six extraction
  negatives; in 2023, a control at five sites and an extraction control. Only one has reads in the
  ASVs kept: the North River control (NOR-C), with 84 reads of *Polydora cornuta*, which the North
  River samples do not have.
- FAIRe-fier: *Success* for both sheets, with no mandatory term left empty.
- FAIRe to Darwin Core: 1,046 presence records (600 from 2019, 446 from 2023), every one with its
  DNA sequence, and the 23 controls left out.

Questions for the authors:
- what the control codes mean (FC, LC and ENEG in 2019; C in 2023);
- the dates of the 2023 samples;
- the sequencing runs and platform for each year;
- why RSE-3 is left out of the published table;
- whether the 27 differences are curation or swapped columns.

## Things to know about these data

- **No sequences behind the names in the Dryad files.** The ASV table sums the reads of each
  species. The FASTA files on Dryad hold every ASV, but nothing links an ASV to a species. So the
  records can't carry the sequence that identified them, and the identifications can't be checked
  or redone from the records. The authors' per-ASV files close that gap (see *With the sequences*,
  below).
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
