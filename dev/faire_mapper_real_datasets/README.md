# FAIRe mapper on four published eDNA datasets

A trial of the FAIRe mapper (`tools/faire_mapper`) on real deposits, to see how much of a typical
published eDNA dataset can be turned into FAIRe with the tools, and what is left for a person.

## Datasets

All four are from Dryad, which publishes data under CC0 1.0 ([Dryad terms](https://datadryad.org/terms)).
The `data/` folder holds the sample table used from each, and the methods or README text converted to
plain text with pandoc.

| Name | Dataset (Dryad DOI) | What the deposit holds | Sample table used |
|---|---|---|---|
| mathon | Processed 12S fish eDNA sequences and visual census data, Mathon et al. ([10.5061/dryad.3xsj3txj2](https://doi.org/10.5061/dryad.3xsj3txj2)), marine, 5 regions | README; one metadata CSV; per-region MOTU tables; headerless plate files; visual census tables | `Metadata_eDNA_global_V6.csv`: 534 filters, 52 columns |
| sacco | Metabarcoding under Brine: microbial ecology of five hypersaline lakes at Rottnest Island ([10.5061/dryad.xd2547dh6](https://doi.org/10.5061/dryad.xd2547dh6)), 16S | README and methods excerpt (docx); mapping file (xlsx); FASTQ files | `mapping_file_Sacco_et_al.xlsx`: 52 rows (50 samples, 2 extraction controls), 6 columns |
| vanderheyde | Taking eDNA underground: eDNA detection of subterranean fauna in groundwater ([10.5061/dryad.dv41ns22g](https://doi.org/10.5061/dryad.dv41ns22g)), 18S | methods (docx); sample data (CSV); ZOTU table | `Barrow_18S_sample_data2.csv`: 299 rows, 20 columns |
| jackman | eDNA in a bottleneck: fish metabarcoding in megadiverse freshwater systems, Jackman et al. 2021 ([10.5061/dryad.j6q573ncq](https://doi.org/10.5061/dryad.j6q573ncq)), 12S MiFish | methods (docx); README workbook with extraction and PCR sheets | `README-file.xlsx`, sheet `DNA_Extractions`, headers on row 2: 47 rows, 7 columns |

## Method

1. **Answer keys.** A separate agent, acting as a FAIRe curator, wrote an answer key for every column
   of the four tables (`gold/`), from the data, the methods text and the FAIRe checklist v1.0.2. It
   did not see the mapper, its code or its output. Each key gives the best term, other acceptable
   terms, and a note. This is one curator's reading; the ambiguous columns are listed in the notes.
2. **Mapper.** `faire_mapper.py map` on each table, metabarcoding, with the sample types of the study.
3. **Model answers.** The columns sent for review were answered by a stand-in for the language model:
   Claude Sonnet, run as a separate agent that saw only the prompts `faire_mapper_adjudicate.py
   --dry_run` writes (`standin_answers/*.adjudication.json`). The mapper was then run again with
   those answers.
4. **Methods text.** `faire_mapper_methods.py --dry_run` wrote one prompt per dataset: the methods
   text and the mandatory and highly recommended FAIRe terms the table did not cover. The same
   stand-in answered it (`standin_answers/*.methods.json`), and the script checked every answer.

`run.sh OUTDIR` repeats steps 2 to 4 with the saved answers and scores the result (`score.py`).

Order of work, for reading the results: version 0.1.0 was run first, as frozen after the benchmark.
It could not read the mathon table (Windows-1252 text, separated by semicolons). The reading fixes
in 0.2.0 were made after that failure, and the routing fixes after seeing the errors below, so the
0.2.0 results on these four datasets are not independent. Neither change altered any benchmark
result (`dev/faire_mapper_benchmark`).

## Results: matching columns to terms

Totals over the four tables: 85 columns, 40 of which have a FAIRe term in the answer keys.

| Run | First choice right (of 40) | Right term in shortlist | Accepted columns right | Columns without a term left unmatched (of 45) |
|---|---|---|---|---|
| 0.1.0, reading fixed only | 22 (55%) | 35 (88%) | 21 of 27 (78%) | 34 (76%) |
| 0.1.0 with model answers | 31 (78%) | 35 (88%) | 31 of 35 (89%) | 42 (93%) |
| 0.2.0 | 22 (55%) | 35 (88%) | 21 of 25 (84%) | 34 (76%) |
| 0.2.0 with model answers | 31 (78%) | 35 (88%) | 29 of 31 (94%) | 42 (93%) |

"Right" counts the key's best term and the terms it lists as acceptable. On the benchmark the first
choice was right for 81 to 93% of columns and 98 to 100% of accepted columns were right, so real
deposits are clearly harder. Per table scores are in `results/`.

What made the real tables harder:

- **Reading.** Semicolon separators, Windows-1252 text, decimal commas, dates stored as Excel serial
  numbers in a CSV (43280), dates as dd.mm.yy, times as fractions of a day, a title row above the
  headers. 0.2.0 reads all of these; the profile notes how the file was read.
- **Several columns for one value.** Mathon has seven sets of coordinates per transect (start, three
  waypoints, half turn, end, and a cleaned start). The mapper gave decimalLatitude to the wrong set;
  the model chose the cleaned start, as the key does.
- **Study-specific columns.** Bore casing and slot details, haul-net abundance and richness, site
  groupings and distances to the coast have no FAIRe term. Without the model the mapper offered weak
  matches for some of them (casing type as assay_type); the model rejected all of these.
- **Look-alike words.** The prefix rule treats *sequence* as *sequencer* and *sample* as *sampler*, so
  Sequence_ID and Sequence_depth were offered instrument, and Sample_year samp_collect_device. The
  model rejected them.
- **Terms outside the shortlist.** The model may only choose among the mapper's candidates. Four of
  the six columns still missed with the model had their term outside the shortlist: Sample_year
  (eventDate), Sequence_depth (output_read_count), `DNA []` (concentration) and data_manager
  (recordedBy). In two of these the model said what the column was but could not choose it.
- **Identifiers shared by replicates.** Sacco's Sample_ID names a sampling point shared by five
  replicate filters; the key maps it to materialSampleID, the mapper accepted samp_name (which FAIRe
  requires to be unique).

## Results: values from the methods text

The stand-in model gave 5 to 26 values per dataset, every one with a quote. All quotes were found in
the text; values that were inferred, outside the allowed values, or missing their unit were sent for
review.

| Dataset | Text available | Values supported | For review | Mandatory terms still missing after table and text |
|---|---|---|---|---|
| mathon | README only (methods are in the paper) | 3 | 2 | 9 |
| sacco | methods excerpt | 11 | 9 | 14 |
| vanderheyde | full methods | 17 | 9 | 11 |
| jackman | short methods, lab work cited to another paper | 9 | 3 | 15 |

The values found were mostly correct on reading the texts: filter pore size and material, extraction
kit, PCR mix, cycling, replicates, sequencing platform and kit, target gene, taxonomic group, controls,
sterilisation, reference databases. The stand-in left out primer sequences, which none of the texts
give, rather than supplying them from memory. Two cautions: the stand-in gave Illumina MiSeq's OBI
identifier from memory (marked inferred, so sent for review), and it checked its own quotes with a
script, which a model called through the API cannot do. A run against the API is still needed.

Mandatory terms missing in all four datasets after both steps:

| Missing term | Where it could come from |
|---|---|
| pcr_primer_forward, pcr_primer_reverse | Two texts name the primers (Bact16S_515F/806R, MiFish) and two cite them (Pochon et al. 2013, Sales et al. 2021). A curated table of primer names and sequences would fill most of these. Primer names were not asked about in this trial; 0.2.0 now asks by default. |
| assay_name | A name the curator chooses, e.g. from the gene and primer names |
| env_broad_scale, env_local_scale, env_medium | The habitat is clear from the texts (hypersaline lake, groundwater bore, coral reef, Amazon stream), but FAIRe needs ENVO terms. The model could propose them, checked against ENVO through the EBI Ontology Lookup Service. |
| project_id, recordedBy, project_contact | Only the Mathon README gives people. All four have a DOI, and the repository's DataCite record lists authors and title. |
| seq_run_id, lib_id | Not in any deposit except as file names (sacco); Jackman states a single sequencing run |
| eventDate, coordinates | Missing from the sacco and jackman tables; van der Heyde gives only the year. These have to come from the authors. |

## How easy were they?

- **mathon:** the richest table but the hardest to read: format problems, many coordinate and time
  columns, sub-project codes. With 0.2.0 and the model, 17 of 19 columns with a FAIRe term were right.
  The deposit has no methods text, so almost all project-level values (primers, gene, sequencing) are
  missing.
- **sacco:** a small, clean mapping file without dates, coordinates or habitat, and a detailed
  methods excerpt. The text supplied most of the laboratory metadata; the sampling metadata is absent.
- **vanderheyde:** a tidy table with coordinates, depth, volume and control flags, plus detailed
  methods; the most complete of the four. Dates are given only as years.
- **jackman:** the sample table is a laboratory sheet inside a README workbook, without coordinates;
  the methods defer to another paper for laboratory detail.

None of the four could be made complete FAIRe from the deposit alone. The tools cover the column
mapping well with the model's help, and the methods text fills much of the project-level metadata
when the deposit includes it. The remaining gaps are predictable (primer sequences, ENVO terms,
people and identifiers, dates and coordinates) and mostly fillable from other sources, which points to
the next tools.

## Changes made to the mapper from this trial (0.2.0)

- Reads semicolon- and tab-separated text, Windows-1252 and Latin-1 text and decimal commas; records
  how a file was read in the summary.
- Recognises dd.mm.yy dates, and integers that may be Excel serial dates for date terms (with a hint
  to convert them).
- A column whose values vary is not accepted for a project-level term (rep and project in mathon).
- When answers give one term to several columns, the best-matching column keeps it and the others go
  to review.
- A column left unmatched because its best term went to another column says so.
- The list of mandatory terms not covered leaves out the assay type and checklist version (set by the
  tool) and terms only mandatory for the other assay type.
- New `faire_mapper_methods.py` for values from methods text, with the checks above
  (`test_methods_checks.py`).

## Suggested next steps

1. Let the model suggest a checklist term outside the shortlist, checked against the checklist and
   always routed to review (four of the six remaining misses).
2. Stop the prefix rule matching agent nouns (*sequencer*, *sampler*) to the base word.
3. Treat repeated values as a conflict for samp_name, so replicate-group identifiers go to
   materialSampleID.
4. A curated primer table (name, sequences, reference) to fill pcr_primer_forward and reverse.
5. ENVO suggestions checked against the ontology.
6. A small tool that reads a dataset DOI's DataCite record for project_id, people and title.
7. Run steps 3 and 4 against the API, and repeat with answer keys from a FAIRe curator.
