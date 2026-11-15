# Reading the methods of one eDNA paper for FAIRe terms

You are building a test set for a tool that reads the methods of environmental DNA (eDNA) papers and suggests values for FAIRe metadata terms. Your values will be compared with the tool's, and a person will check both against your excerpts. An accurate value with a word-for-word excerpt matters more than filling every term.

You have three files in your folder:
- `paper.pdf`: the paper's main PDF (no supplements, on purpose).
- `../terms.tsv`: the 109 FAIRe terms, one per row, with the section, FAIRe level, what FAIRe asks for, unit, allowed values, where it usually appears, how papers often word it, an example value and what to watch out for. Read it all before you start.
- this file.

## What to do

1. Read the paper's methods in full with the Read tool (use the `pages` parameter), including tables and their captions. Use the introduction, results and discussion only where the methods point to them. Use only the main PDF: where the methods send the reader to a supplement for a step ("PCR conditions are given in Table S2"), add one row with Workflow ID NN.all, the value empty, `In supplement` as Stated or inferred, and the sentence that points to the supplement as the excerpt.
2. Decide the paper's workflows. A workflow is one path from sample to taxa that the paper processed in its own way: usually one per marker (assay). Make separate workflows too where sample types, sequencing platforms or bioinformatic pipelines differ in ways that change the values. Workflow IDs are the paper number and a workflow number: 33.1, 33.2.
3. Go down `terms.tsv` one term at a time, all 109 terms, and record a value for each term the PDF gives a value for. A typical metabarcoding paper gives 25 to 50 values; a paper with many assays gives more.

## Rules for every value

- Every value needs an excerpt: the sentence or table cell it came from, copied word for word, with the paper's own symbols and units (µL, °C, ×). If you cannot quote it from the paper, do not give the value. Keep excerpts to the sentence or cell that holds the value; do not join distant sentences with "...".
- Write the value in FAIRe form, as `terms.tsv` describes: an allowed value where the term has a list, a number without its unit where FAIRe fixes the unit (25 for a 25 µL reaction), and several databases separated by " | ".
- When the paper says nothing about a term, leave it out. Do not infer "none", or a setting or threshold the paper does not state, and do not fill in a typical protocol or take values from papers it cites. If the paper only cites another paper or protocol for a step, add one row for that step with the value empty, `Cited protocol` as Stated or inferred, and the citation sentence as the excerpt.
- Mark as Inferred any value you worked out rather than read (from several stated facts, or from what a kit is known to do), and say how in the notes. Converting units or wording (30 s to 0.5 min; "2 × 300 bp" to paired end) still counts as Stated.
- Give values per workflow where the assays differ (primers, PCR conditions, reference databases, filtering settings). Where a value is the same for all workflows, give it once with NN.all.
- A term with a value and a unit (samp_size and samp_size_unit, say) needs both rows.
- If the PDF text looks garbled (a missing minus sign, a broken symbol), leave the value out and say so in the notes.

## Things that are easy to get wrong

- Use only the paper's own eDNA samples. Leave out methods for reference specimens, voucher tissue and Sanger sequencing of reference sequences, except to describe a custom database in otu_db_custom.
- Two-step library preparation: the first PCR (gene primers) goes in the pcr_ terms and the second (indexing or library) PCR in the pcr2_ terms. Never join the two in one value.
- pcr_cond: `initial denaturation:95_15;denaturation:95_0.5;annealing:54_1.5;elongation:72_1.5;final elongation:72_10;40` (°C, minutes, cycles last). A two-step cycle (denaturation, then a combined annealing and extension) has annealing and no elongation. Touchdown programmes: give the main phase and describe the rest in pcr_method_additional.
- pcr_primer_conc is the stock concentration (µM) of the primer added. "0.4 µM of each primer" in the reaction is a final concentration: put it in custom_mm, not pcr_primer_conc.
- Volumes are in µL. A template given as an amount (10 ng of DNA) is not a pcr_dna_vol.
- samp_size is what was collected; samp_vol_we_dna_ext is what went into the extraction. Give samp_vol_we_dna_ext only when the paper says how much was extracted, or that the whole filter was.
- samp_collect_device is what took the sample from the environment (Niskin bottle, bucket, bottle, grab), not the syringe, pump or filter unit used to filter it.
- nucl_acid_ext_kit is a commercial kit. CTAB, Chelex and phenol-chloroform are methods, not kits.
- dna_cleanup is clean-up of the DNA extract (inhibitor removal). Clean-up of PCR products (AMPure beads) goes in lib_screen.
- sop_bioinformatics, nucl_acid_ext and nucl_acid_amp are links or citations to a protocol, script or pipeline. Leave them out if the paper gives none; do not list programs or write "two-step PCR" there.
- otu_clust_cutoff is 100 for ASVs, ESVs or zOTUs (DADA2, UNOISE3, deblur).
- tax_assign_cat uses FAIRe's categories: BLAST or VSEARCH searches are sequence similarity; a naive Bayes classifier (RDP Classifier, DADA2 assignTaxonomy, q2-feature-classifier) is sequence composition.
- Name software and versions as the paper writes them (BLAST+ 2.13.0, cutadapt v3.4), with the settings in the term for that step.
- Description terms (sterilise_method, samp_mat_process, nucl_acid_ext_modify, inhibition_check, lib_screen and the *_additional terms) are short, one or two sentences, and cover only their own step.
- The primer terms (assay_name, primer names and sequences, target gene, amplicon size) are included. Give only the gene-specific part of each primer sequence, without adapters, tags or indexes.

## What to write (in your folder)

Write plain tab-separated files with the Write tool: one line per row, a tab between columns, no tabs or line breaks inside a field, and a header line as shown.

`values.tsv`
```
workflow_id	term	value	excerpt	where	stated_or_inferred	confidence	notes
```
- workflow_id: 33.1, or 33.all; term: exactly as in terms.tsv; stated_or_inferred: Stated, Inferred, Cited protocol or In supplement; confidence: High, Medium or Low; where: section heading, table or page.

`workflows.tsv`
```
workflow_id	workflow	assay_or_marker	sample_type	platform_or_method	bioinformatics_pipeline	notes
```

`paper.md`: the citation (first author, year, journal, DOI), the parts of the paper you read, the steps the paper leaves to a supplement, and what you were unsure of.

## Independence

This reading must be independent. Use only the three files above. Do not open, list or search any other folder or file on this machine, do not run any program that extracts text from the PDF, and do not search the web. Read the PDF only with the Read tool.
