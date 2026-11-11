# FAIRe mapper on two Australian eDNA datasets

A second trial of the FAIRe mapper (`tools/faire_mapper`) on published data, with the kind of input
a researcher would typically have: a sample table and the methods section of a paper. First run on
3 November 2026 with mapper version 0.3.0, with no changes made for these datasets,
so those results are independent. The mapper was then changed (version 0.4.0) to fix the main gaps
found, and the trial run again with a new step that writes a FAIRe workbook. The 0.4.0 results are
not independent.

## Datasets

| Name | Study | Sample table | Methods text |
|---|---|---|---|
| dibattista | DiBattista et al. 2024, seasonal eDNA on a coral reef, Lizard Island, *Coral Reefs* ([10.1007/s00338-024-02594-6](https://doi.org/10.1007/s00338-024-02594-6)); data on Dryad ([10.5061/dryad.jq2bvq8fh](https://doi.org/10.5061/dryad.jq2bvq8fh)) | `LI_sampling_metadata.csv` from Dryad: 72 filters, 14 columns, Windows-1252 text | The paper's Methods section, and the Dryad README, which describes each column |
| kimberley | West et al. 2021, biogeographic break in the Kimberley, *Diversity and Distributions* ([10.1111/ddi.13228](https://doi.org/10.1111/ddi.13228)); data on Dryad ([10.5061/dryad.8kprr4xmm](https://doi.org/10.5061/dryad.8kprr4xmm)) | `site_metadata_TableS1.csv`: Table S1 of the supplement, 71 sites, 9 columns, made with `parse_kimberley_s1.py` | The paper's Methods section and supplement Section S1 (laboratory processing) |

Licences: both Dryad deposits are CC0 1.0. The Kimberley paper is open access under a Creative Commons
Attribution licence, so its methods text is stored here with the citation above; the supplement states
no licence of its own, and Section S1 and Table S1 are used on the same terms. The DiBattista paper is published under an exclusive licence to
the International Coral Reef Society, so its methods text is not stored: to rerun, extract the Methods
section of the paper (from "Methods" to the line before "Results") with `pdftotext`, remove page
headers and numbers, and save it as `data/dibattista/methods.txt`.

`data/kimberley/Actinopterygii_read_abundance_matrix.xlsx` (Dryad) is the Kimberley read matrix: 71
sites by 362 bony fish taxa, with reads summed per taxon and no sequences, followed by the site
details. The paper says the reads were rarefied, ASVs merged by taxonomy, and the three assays then
combined by taxonomic group (Actinopterygii, Elasmobranchii, Reptilia). It was used from the second
run (0.4.0).

## Method

As in the first trial (`dev/faire_mapper_real_datasets/README.md`):

1. **Answer keys** (`gold/`). A separate agent, acting as a FAIRe curator, wrote a key for every
   column from the data, the methods, the Dryad README and the FAIRe checklist v1.0.2. It did not see
   the mapper or its output.
2. **Mapper**: `faire_mapper.py map` on each table, metabarcoding, sample type Water.
3. **Model answers**: a stand-in for the language model (Claude Sonnet, run as a separate agent) answered
   the review requests and the methods prompt (`standin_answers/`). The scripts checked every answer.
4. **Primer lookup**: `faire_primers.py text` on each methods text.
5. **FAIRe workbook** (0.4.0 only): `faire_mapper_apply.py` with the crosswalk after the model's
   answers (matches for review included), the methods values marked *supported*, the country
   (Australia) and the assay names, and for Kimberley the read matrix as the OTU table, then
   FAIRe-fier (`tools/fairefier`) on the workbook. With `RSCRIPT` set, FAIRe2MDT then converts the
   Kimberley workbook (`results/kimberley.MDT.xlsx`).

`run.sh OUTDIR` repeats all steps with the saved answers and scores the result (`score.py`). The 0.4.0
outputs are in `results/` (per-column scores, methods values, primer candidates, the workbooks, their
logs and the FAIRe-fier issues); the 0.3.0 outputs and stand-in answers are in `results/0.3.0/` and
`standin_answers/0.3.0/`. The review requests changed in 0.4.0, so the stand-in answered them again
(`standin_answers/*.adjudication.json`); the methods answers are the same.

## Results with 0.4.0

The 0.4.0 changes were made in two steps on 3 and 4 November. The second added the data dictionary
(DiBattista's Dryad README, which describes every column, is given as one), the common names *filter
size* and *days frozen*, place words for geo_loc_name (region, subregion, reef, island) and a check
that target_subfragment holds amplicon regions (V4, ITS2), not place names. The stand-in answered the
new review requests, which now carry the descriptions.

| Dataset | First choice right | Accepted columns right | Columns without a term left unmatched |
|---|---|---|---|
| dibattista, mapper alone, step 1 | 7 of 9 | 4 of 5 | 3 of 5 |
| dibattista, with model, step 1 | 7 of 9 | 9 of 10 | 3 of 5 |
| dibattista, mapper alone, step 2 (with the README as dictionary) | 9 of 9 | 6 of 6 | 3 of 5 |
| dibattista, with model, step 2 | 9 of 9 | 11 of 11 | 3 of 5 |
| kimberley, mapper alone, step 1 | 5 of 5 | 6 of 6 | 1 of 4 |
| kimberley, with model, step 1 | 5 of 5 | 8 of 8 | 1 of 4 |
| kimberley, mapper alone, step 2 (no dictionary) | 5 of 5 | 7 of 7 | 1 of 4 |
| kimberley, with model, step 2 | 5 of 5 | 8 of 8 | 1 of 4 |

`results/` holds the step 2 outputs.

- **geo_loc_name from several columns.** DiBattista's Sampling country, Reef Location and Sampling
  Location now build "Australia: Great Barrier Reef, Lizard Island (Big Vicky's Reef)". Reef Location
  and Sampling Location each have one value, so their order is a guess (reef first, from the header)
  and all three go to review. In Kimberley, the model's answer for Subregion joins it with Location:
  "Australia: Dampier Peninsula, Gantheaume Bay", with the country from the form.
- **"1 L" and "0.2 micron".** Amount filtered fills samp_size and samp_size_unit, and Filter size
  fills size_frac with 0.2, both for review; the model chose them too.
- **Step 1 still had wrong or missed:** Sample processing (samp_mat_process; the key says recordedBy)
  and Days frozen (samp_store_dur was not in the shortlist). In step 2 the README describes Sample
  processing as "the person that filtered the water sample", which points to recordedBy (for review;
  the model chose it too), and Days frozen matches samp_store_dur by its common name and its
  description, written as P316D in the workbook. Kimberley's Subregion now joins geo_loc_name without
  the model, as its values are place names, not amplicon regions.

**FAIRe workbooks.** Both workbooks were written (`results/*.faire.xlsx`, with logs). FAIRe-fier read
them and reported errors only for:

- mandatory terms still empty: recordedBy, project_contact, the primer sequences (for review only),
  samp_category, env_broad_scale, and env_local_scale for DiBattista;
- `checkls_ver`, written as FAIRe-ator writes it (a known issue for the FAIRe authors);
- Kimberley's habitat classes (Inshore, Coastal), which need ENVO terms for env_local_scale.

The converted values (ISO dates, geo_loc_name, numbers and units) passed.

**The Kimberley read matrix.** Apply mapping read it with samples as rows: 71 sites (all matching
samp_name), 362 taxa, and the site details after the counts (Site.1, Latitude ... Sampling season)
left out. With no taxonomy table, the names gave 220 species, 128 genera and 14 families; the ranks
above them are empty, for edna2obis's *match taxa* to fill. dna_sequence is empty, as the matrix has
none. The tool also wrote 71 experimentRunMetadata rows (samp_name, assay, run ID; lib_id empty).
FAIRe2MDT converted the workbook: 71 samples, 362 taxa. Because the matrix combines all three assays
and is rarefied, it is written under 16SFish only to try the step; a FAIRe submission would need the
authors' per-assay ASV tables with sequences. Warnings were for the
user-defined fields and for coordinates with fewer than five decimal places (some source values have
three or four; others lost a trailing zero when stored as numbers, such as -13.99230). One caution
from the logs: values from the methods text are written for every sample, and DiBattista's storage
temperature (-20 °C) does not apply to the February samples, which were filtered fresh.

## Results with 0.3.0: matching columns to terms

| Dataset | Columns | With a FAIRe term in the key | First choice right | Accepted columns right | Columns without a term left unmatched |
|---|---|---|---|---|---|
| dibattista, mapper alone | 14 | 9 | 4 | 5 of 6 | 3 of 5 |
| dibattista, with model | 14 | 9 | 5 | 5 of 7 | 3 of 5 |
| kimberley, mapper alone | 9 | 5 | 5 | 6 of 6 | 1 of 4 |
| kimberley, with model | 9 | 5 | 5 | 7 of 7 | 1 of 4 |

Coordinates, dates, sample names, habitat and depth were matched in both tables, and both date formats
were recognised (12-Feb-19 and 06/09/2017). The Kimberley table, with plain headers, was mapped almost
perfectly. The DiBattista table shows where the mapper falls short:

- **Sample processing** (the person who filtered each sample) was accepted as samp_mat_process. The
  key says recordedBy. The Dryad README says what the column holds, but the mapper reads only headers
  and values.
- **Filter size** ("0.2 micron") and **Days frozen** (316, 0) were not matched. The keys say size_frac
  and samp_store_dur. Neither term was in the shortlist, so the model could not choose it.
- **Amount filtered** ("1 L") was offered unit terms (samp_vol_we_dna_ext_unit, then samp_size_unit
  from the model). The key says samp_size, with the value and unit split into two terms.
- **Place names in several columns.** FAIRe's geo_loc_name is built from country, region and locality
  ("Australia: Queensland, Great Barrier Reef, Lizard Island"). The tables hold these in two or three
  columns, and the mapper gives each term to one column only, so the other columns were pushed to
  unrelated terms: Reef Location to sequencing_location, Kimberley Location to samp_store_loc.
- **Look-alike matches** fixed by the model: Sampling country (env_medium, changed to geo_loc_name)
  and Subregion (target_subfragment, changed to geo_loc_name).

## Results with 0.3.0: values from the methods text

| Dataset | Values supported by a quote | Sent for review | Mandatory terms still missing |
|---|---|---|---|
| dibattista | 22 | 33 | 11 |
| kimberley | 22 | 95 | 10 |

The text supplied the laboratory metadata well in both: sterilisation, filter pore size and material,
volume, storage temperature, extraction kit, PCR mix, cycling and replicates, platform, library
preparation, reference database and contamination screening. Most of the items for review are primer
details from the primer table (below). As in the first trial, the stand-in checked its quotes with a
script, which a model called through the API cannot do.

Mandatory terms missing in both after the table and the text: recordedBy, project_contact, project_id,
samp_category, neg_cont_type, pos_cont_type, env_broad_scale, assay_name, lib_id and seq_run_id
(and env_local_scale for DiBattista). The primer sequences were offered for review only.

## Results with 0.3.0: primer lookup

Each lookup took about 51 seconds on the methods text (about 1 second since 5 November, when the primer table's names were indexed once per run). After the primer table fixes in 0.4.0 the
Kimberley lookup gives 12 candidates (the two COI rows entered in error are gone). Since find primers
reads sequences written in the text (0.5.0), the same 12 come in a new order: first the four pairs the
Kimberley methods give as sequences (COI elasmobranch with FishF1 and with FishF2, 16S reptile and
Fish16S), then the 8 that match only a name, part of a name or a reference. DiBattista's methods give
no sequences, so its 4 candidates are unchanged.

- **dibattista**: all three assays found (Fish16S, CoralITS2, CoralITS2_acro). One false candidate:
  Crust16S, found through the Berry et al. 2017 citation, which is the reference for both 16S pairs.
- **kimberley**: all three assays found (16S fish, COI elasmobranch, 16S reptile), among 14
  candidates. The false ones came from a short generic name (16SF), part-name matches ("eDNAF" matched
  three 28S and COI pairs) and cited references that have several pairs (Nester et al. 2020, Berry et
  al. 2017).
- **Primer table errors seen** (fixed in 0.4.0, see `tools/faire_mapper/primers/README.md`):
  CoralITS2 and CoralITS2_acro were listed with target gene 28S rRNA (they target ITS2), one was named
  "CoralTTS2 acro", and two COI elasmobranch rows paired FishF1 forward with FishF2 reverse, or gave
  COI-MINIR as the forward primer.

## Suggested mapper changes from this trial

Items 1 to 4 and the primer table fixes in 6 are done in 0.4.0.

1. Read a data dictionary (column name and description, such as a Dryad README) alongside the table,
   and use the descriptions in matching and in the model's prompt.
2. Let one term be built from several columns, starting with geo_loc_name, so the clash rule does not
   push the other columns to unrelated terms.
3. Split a value and its unit ("1 L", "0.2 micron") into the value term and its unit term.
4. Add header aliases: filter size and pore size for size_frac, days frozen and storage time for
   samp_store_dur (as ISO 8601 durations).
5. Primer lookup: drop matches on short generic names and part names unless a sequence or the full
   name is also in the text, and treat a cited reference as supporting evidence only.
6. Fix the primer table rows above, and speed up the lookup.
