# FAIRe conventions to follow

These come from the FAIRe guidelines (https://fair-edna.github.io/guidelines.html), the FAIRe
checklist v1.0.2 bundled with the tools, and what trials of the FAIRe tools on published datasets
showed people most often get wrong.

## Contents

- Missing values
- Dates and times
- Samples, controls, assays and runs
- Commonly confused terms
- Values that must come from a source
- Terms not in FAIRe
- Judgement calls
- Minimum or complete

## Missing values

When a mandatory term has no value, FAIRe uses the INSDC missing-value terms, and recommends them
for other terms too. Use only these, exactly as written, and only when the researcher says which
applies:

- `not applicable: control sample`, `not applicable: sample group`, `not applicable`
- `missing: not collected`, `missing: not collected: synthetic construct`,
  `missing: not collected: lab stock`, `missing: not collected: third party data`
- `missing: not provided`, `missing: not provided: data agreement established pre-2023`
- `missing: restricted access`, `missing: restricted access: endangered species`,
  `missing: restricted access: human-identifiable`

Apply mapping writes `not applicable: control sample` in the empty mandatory cells of controls by
itself. Never fill a gap with a plausible guess.

## Dates and times

- eventDate is ISO 8601. Times of collection are kept as **local time** with the UTC offset
  (2022-03-15T04:00+11:00), as daily biological cycles follow local time. Set the offset with
  `start --utc_offset`. If the table gives only UTC times, ask for the local offset.
- Dates such as 03/04/2023 can be read two ways. Ask which order, and set `start --date_order`.
- The original dates and times are kept as written in verbatimEventDate and verbatimEventTime.

## Samples, controls, assays and runs

- One row per sample, and each samp_name used once. A name shared by replicate filters is a site or
  sampling point (materialSampleID), not samp_name.
- Controls are rows of the sample table, marked by samp_category (sample, negative control,
  positive control, PCR standard) with neg_cont_type or pos_cont_type (field negative, extraction
  negative, PCR negative ...). Controls named only in their sample names need a column added.
- An assay is one primer set (or one qPCR assay). assay_name has no spaces, and for targeted assays
  no underscores (FAIRe-fier reads it from detected_notDetected_<assay_name> after the last
  underscore). FAIRe holds one set of PCR conditions per assay, so the same primers run on two
  machines with different conditions are two assays (OlsonViiA7, OlsonFranklin).
- A library (lib_id) is one amplicon of one sample in one sequencing run.
- OTU or ASV tables of the same assay from different sequencing runs are kept separate: FAIRe has
  one table for each assay and sequencing run. Give each its run with `--otu ... run=RUN_ID`.
- A raw table holds every ASV; a final table holds the curated taxa. Say which with `stage=raw` or
  `stage=final`.

## Commonly confused terms

Always ask the question that tells these apart, however strong the match:

- **Depth**: minimumDepthInMeters and maximumDepthInMeters (the depth the sample was taken from)
  versus tot_depth_water_col (the depth of the water at the site).
- **Amounts**: samp_size (the amount collected from the environment, such as 1 L of water) versus
  samp_vol_we_dna_ext (the amount that went into the DNA extraction, such as 500 mL when half the
  filter was extracted).
- **Taxa**: targetTaxonomicAssay (what the primers amplify, such as vertebrates) versus
  targetTaxonomicScope (what the study set out to detect, such as fish).

## Values that must come from a source

- **Primer sequences**: from the researcher's methods, matched to the bundled reference table
  (`methods`, `primers-lookup`, `primers-use`), or as the researcher gives them.
- **Instruments**: the methods tool adds OBI identifiers from its vocabulary. Do not add others from
  memory.
- **ENVO terms** (env_broad_scale, env_local_scale, env_medium): `label [ENVO:00000000]`, with the
  identifier checked in the ENVO ontology (https://www.ebi.ac.uk/ols4/ontologies/envo) or given by
  the researcher.
- **People and contacts**: only as the researcher gives them. recordedBy lists names separated by
  ` | `; project_contact is an email.

## Terms not in FAIRe

A column with no FAIRe term is kept under its own name as a user-defined field. The mapper may offer
a MIxS or Darwin Core term first, as the FAIRe guidelines prefer an existing standard's term to a
new name; the researcher chooses.

## Judgement calls

Some terms can be read more than one way, and the person entering the data decides. Give the
readings in a sentence, propose one, record their choice and move on. These details matter less for
later uses of the data than the samples, dates, places, controls and taxa. Examples:

- **Storage temperature**: samp_store_temp is for the sample before any processing (water before
  filtering), and prepped_samp_store_temp for the processed sample (the filters). When the methods
  give only one temperature, ask which it was.
- **Identity cut-offs**: when the methods give one cut-off for any assignment and a stricter one for
  species names (85% and 98%, say), FAIRe's definition ("minimum percent identity for taxonomic
  assignment") points to the first for tax_class_id_cutoff and tax_class_query_cutoff, with the
  species rule in tax_class_other. Some researchers prefer the species cut-off; propose the first
  and take their choice.
- **Analyses done for a paper**: a sentence such as "ASVs were merged by taxonomy" describes the
  paper's analyses. If the tables in the workbook are per ASV, say so in the value or leave it out.

## Minimum or complete

The mandatory terms (some only under conditions) make a minimum dataset. After them,
`gaps --recommended` lists the highly recommended terms still empty that can apply to the study;
`references/faire-terms.md` lists both. Offer only those the files or the researcher can answer, as
one checklist; do not ask about every optional term.
