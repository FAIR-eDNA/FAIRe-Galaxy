# Finding method details in methods text, by rules

A trial of **FAIRe mapper: find method details** (`tools/faire_mapper/faire_method_details.py`), which
reads a study's methods and proposes values for the FAIRe terms about filtration, DNA extraction, PCR,
library preparation, sequencing and bioinformatics, each with the sentence it came from. The values
go into a review sheet that a person checks, and apply mapping reads the reviewed sheet as values for
the whole project.

The tool came from the FAIRe team's second review of the Shiny app (14 November 2026), which asked
whether more than primers could be found in the methods: "a mapping and review might still be easier
than a user having to fill out a spreadsheet de novo".

## How it works

The tool works by rules, without a language model, so it runs offline and gives the same answer each
time. Following the project's rule for the mapper (automate only what FAIRe defines, common pipeline
outputs, or patterns seen in two or more datasets, and send everything else to a person), the rules
look for two kinds of thing.

The first is named things: sequencing instruments, thermocyclers, master mixes, extraction kits,
filters, sampling devices, software, pipelines, reference databases and sequencing facilities. These
are listed in `tools/faire_mapper/method_details/vocabulary.tsv`, one row each, so a missing kit or
program is one line to add. The software rows come from the Galaxy eDNA lab's tool evaluation (the
workbook of tools and published workflows made at the start of the Galaxy project), which also gives
the step each program does (trimming, merging, denoising and so on). The OBI identifiers of the
instruments come from the OBI ontology, through the LinkML value sets, and the FAIRe checklist's own
examples; instruments without a known identifier are written without one, with a note.

The second is the ways methods state a value, each seen in at least two of the development texts: a
PCR programme ("initial denaturation at 95 °C for 15 min, followed by 40 cycles of ..."), a reaction
volume ("in 25 µL reactions"), a template volume ("2 µL of DNA template"), replicates ("in
triplicate"), a pore size, a storage temperature, a minimum length, a number of expected errors or a
Phred score, a minimum overlap, mismatches allowed, a minimum number of reads, an identity or query
coverage threshold, and sentences about bleach, filtration, library clean-up, the lowest common
ancestor step and checks against species' distributions.

Some choices matter more than others:

- When the text is a whole paper, only the Methods section is read (from its heading to the Results,
  Discussion or References heading), with any supplementary methods after the references. The rest of
  a paper names tools and kits that other studies used. A table's "Reference" column label is not taken
  for the references heading: a references heading counts only when references follow it.
- A paragraph about specimens or vouchers (a reference library made from tissue, say) is left out of
  the laboratory rules, though it still counts for the reference database.
- Software is assigned to a FAIRe term by the step its sentence describes: Cutadapt in a sentence about
  demultiplexing goes to demux_tool, in one about trimming to trim_method, or both.
- A second PCR that adds the indexes gives the pcr2 terms, and the first the pcr terms.
- The storage temperature before filtering goes to samp_store_temp and the one after it to
  prepped_samp_store_temp, as the FAIRe checklist describes.
- Sentences for a descriptive term (sterilise_method, samp_mat_process and so on) are joined into one
  value for the person to shorten. Where a term has several values (two filter materials, say), each is
  listed with a note to keep the one for the eDNA samples.

## Texts

Development texts, used while writing the rules, all in this repository:

| Name | Text | Words read |
|---|---|---|
| seames | SEA-MES report methods (Deagle et al. 2025, CC BY 4.0), `dev/faire_mapper_seames/data/methods.txt` | 2297 |
| kimberley | West et al. 2021 methods and supplement, `dev/faire_mapper_australian_datasets/data/kimberley/methods.txt` | 2416 |
| jackman | Jackman et al. 2021 Dryad methods (CC0), `dev/faire_mapper_real_datasets/data/jackman/methods.txt` | 236 |
| sacco | Sacco et al. Dryad methods excerpt (CC0) | 627 |
| vanderheyde | Van der Heyde et al. Dryad methods (CC0), no Methods heading, read whole | about 1600 |

Held-out text, run once the rules were frozen: the day-night paper of West et al. (2024, *Environmental
DNA* 6: e70018, CC BY), read as a whole paper (9400 words, of which the tool read the 2265 of its
Methods section). Its values had been written by hand, from the paper, for the day-night trial
(`dev/faire_mapper_daynight/project_values.tsv`), before this tool existed. The paper's text is not
stored here; `run.sh OUTDIR PATH` runs it from a local copy.

## Results

`results/` holds the values the tool proposes for each development text (`run.sh results` writes them
again). Across the five, it proposed 12 to 59 values for 12 to 52 FAIRe terms; the short Jackman text
gives few because it refers to another paper for the laboratory work.

On SEA-MES, against the values written by hand for its trial (27 values within the tool's scope), the
tool proposed 20 of them, 2 in part, and missed 5. The two in part: it proposes the 4 °C storage before
filtering as samp_store_temp and the −80 °C storage of the filters as prepped_samp_store_temp, where the
hand-made values put −80 in samp_store_temp; and it gives the filtered volume in litres where the
hand-made values use mL. The five missed are a link to the laboratory protocol and four descriptions
written for the FAIRe record (how the raw and final tables were made, and the screening of non-target
taxa), which are not sentences in the methods.

On the held-out paper, with the rules as frozen, the tool proposed 40 of the 52 hand-made values within
its scope, got 2 wrong, gave 1 under the neighbouring FAIRe term (−80 °C as prepped_samp_store_temp)
and missed 9. The two wrong were the PCR programme and annealing temperature: the paper writes the
range of the two assays' annealing temperatures as "46°C–54°C", with the degree sign on both numbers,
and the tool read the second as −54. The run showed three faults, all general, which were then fixed:
that way of writing a range; soft hyphens that PDFs leave inside words ("two-­step", "MF-­Millipore"),
which hid them from the rules; and a collection volume whose verb was more than 60 characters away.
With these fixed, the tool proposes 44 of the 52, 2 in part (the PCR programme and annealing temperature,
as the range 46–54 for both assays, where the hand-made values give each assay its own), 1 under the
neighbouring term, and misses 5. Of its 52 proposals, none is wrong; two are the species-level identity
and coverage thresholds offered for tax_class_id_cutoff and tax_class_query_cutoff, with a note saying
so.

What it does not do:

- **Calculations.** Half of each filter was extracted, so samp_vol_we_dna_ext is 500 mL, not the litre
  filtered. The tool gives the volume filtered, with the note on samp_size and samp_vol_we_dna_ext that
  propose mapping also gives.
- **Values per assay from a table.** Annealing temperatures listed per assay in a table come out of a
  PDF in pieces. With assay names given, a value in a sentence that names one assay is proposed for it;
  otherwise the person gives the assay.
- **Descriptions for the record**, such as otu_raw_description, and links to protocols.

## A caution

The held-out paper comes from the same research group as the SEA-MES and Kimberley texts, and writes its
methods in much the same way, so these results are likely to be better than for methods written
elsewhere. The rules should be tried on methods from other laboratories (a QIIME 2 study of bacteria,
a MiFish study using Claident, a Nanopore study, say) before the numbers are quoted. Methods text from
journal web pages could not be fetched word for word for this trial.

## A larger trial: 30 papers from other laboratories

The caution above led to a second trial on 30 published eDNA papers chosen for the variety of their
methods (marine, freshwater, soil, sediment, air and plant studies; Illumina, Ion Torrent, PacBio,
Nanopore, qPCR and ddPCR; QIIME, OBITools, DADA2, USEARCH, Anacapa, Claident and other pipelines).
Microsoft Copilot read each paper and its supplements and filled in a workbook of FAIRe values, one row
per workflow, with excerpts. Ten papers were drawn at random as a held-out set (one from each of the
rarer kinds: Claident, long reads, targeted assays, plant markers, soil or sediment), and neither those
papers nor their rows were opened until the rules were frozen. The papers are not stored here.

Copilot's values guided the work but are not a reviewed answer key. They follow FAIRe closely for most
terms, but not for four: they give lists of programs for sop_bioinformatics (FAIRe asks for a protocol
or a link), PCR product clean-ups for dna_cleanup_method (FAIRe means clean-up of the extracted DNA) and
"two-step PCR" for nucl_acid_amp (a link to a protocol). Those four are left out of the scores below, as
is one development paper whose Copilot row is nearly empty. A value agrees when its numbers or names
match Copilot's; the figures count the FAIRe terms for which Copilot gave a value.

| Rules | Development (19 papers, 590 values) | Held out (10 papers, 282 values) |
|---|---|---|
| Before this trial | 219 agree (37%) | 93 agree (33%) |
| After fixing how PDFs are read | 270 (46%) | 118 (42%) |
| Frozen, after working through the development papers | 371 (63%) | 132 (47%) |

Most of the gain that carried over to the held-out papers came from reading PDFs better. pypdf, which
Galaxy uses, gives each page as one block of lines, so a page read as one paragraph and a single
sentence about specimens could hide a page from the rules; Wiley PDFs split words ("fol - lowed",
"two-  step"), some journals use ligatures, superscript reference numbers run into names and versions
("Cutadapt v.1.1687" for v1.16 and reference 87), and MDPI writes degrees as a small circle. The rules
written from the development papers (more ways of naming a two-step library, reaction and template
volumes, sequencing facilities and kits, clustering thresholds, primer stock concentrations, and about
40 kits, databases, programs and pipelines) added 17 points on those papers but 5 on the held-out ones:
much of it fits the wording and products of the papers it came from.

On the held-out papers the frozen rules missed products they had not seen (an M-Sorb-OOM kit, Phire
and Phusion master mixes, an Ion PGM 400 kit), read nothing from three pages of one paper that pypdf
5.1.0 cannot read (a newer pypdf reads them), and cannot read values that sit only in a supplementary
spreadsheet. Some disagreements are Copilot's: zero-radius OTUs are given 100% for otu_clust_cutoff,
as FAIRe asks for ASVs, where Copilot wrote "zOTUs".

The per-term counts from both sets are in `tools/faire_mapper/method_details/reliability.tsv`, which the
tool uses to sort its proposals into values for terms found reliably and values to check.

### The held-out papers checked by a person

A person then checked every held-out value that Copilot or the tool gave against its paper: 373 pairs of
paper and FAIRe term, each judged as Copilot right, tool right, both, neither, or another value. Judged
this way (a value is right when it is what FAIRe asks for, as the paper gives it):

| | Values given | Right | Partly right | Wrong |
|---|---|---|---|---|
| The tool (frozen rules) | 245 | 213 (87%) | 15 (6%) | 17 (7%) |
| Copilot | 282 | 227 (80%) | 25 (9%) | 30 (11%) |

Of the 351 values these papers give, the tool found 213 (61%) and Copilot 227 (65%): the tool proposes
fewer values, and more of them are right. The values for terms the tool counted as found reliably were
right 95% of the time (109 values), those to check 88% (102) and descriptions 56% (34). The 10 values
of the Mandatory term pcr_0_1 were all right. The per-term counts in `reliability.tsv` now come from
these judgments for the held-out papers (and from the Copilot comparison for the development papers),
which moved amplificationReactionVolume and seq_kit to the reliable group and pcr_cond to the values to
check.

The reviewer's notes point to what to improve next:

- Descriptions (samp_mat_process, lib_screen, bioinfo_method_additional, nucl_acid_ext_modify) are often
  too long, or come from another step: bioinformatics under sample processing, steps after extraction
  under changes to the extraction, the processing of tissue under the eDNA samples.
- In one two-step library the second PCR was not separated into the pcr2 terms. A PCR programme has an
  initial denaturation, then cycles of denaturation, annealing and extension, and sometimes a final
  extension; in a two-step cycle annealing and extension share one temperature.
- Where assays differ, values should follow FAIRe's way of giving values per assay.
- A sentence proposed for two different terms is a sign that one of them is wrong.
- pcr_dna_vol is a volume: a template given in nanograms is no value for it.
- Copilot's values without an excerpt could not always be checked, and Copilot often joined the first
  and second PCR into one value.

These held-out papers have now been seen, so rules changed in response to them need new papers to test.

### The development papers' values checked by a person

The same person then judged the development papers' values that rested on Copilot alone: those only the tool
gave, or where the tool and Copilot disagreed (357 values; for terms already judged three times, the rest
were left). Of the 230 values that could be judged from their sentence, 196 (85%) were right, 19 partly right
and 15 wrong; 19 could not be judged without the paper. With these judgments in `reliability.tsv`, 44 terms
now count as found reliably, among them the extraction kit, lysis and separation, the programs for
demultiplexing, trimming, merging and filtering, minimum length and read cut-offs, primer volumes and stock
concentrations, and the identity threshold. The reviewer's notes add to the list of things to improve:

- The volume filtered is not always the volume extracted: a paper that does not say how much was extracted
  should leave samp_vol_we_dna_ext to the person.
- A syringe or filter unit used for filtering is not the sampling device.
- Specimens, macroinvertebrates and samples for morphology are not eDNA samples, whatever words describe
  them.
- Chelex is a reagent, not a kit.
- Programs should be named as the paper names them (SINTAX, BLAST+).

### Changes made after the reviews

Measured against the 901 values the reviewer judged (831 right, 36 partly right, 34 wrong), the changes below
keep 822 of the right values, and drop 11 of the wrong and 7 of the partly right ones. Most of the 9 right
values no longer proposed moved to a better term (a second PCR's programme to pcr2_cond) or were descriptions
that now leave out a sentence from another step.

- Sentences about reads and sequences ("quality filtered", ASVs, cutadapt, DADA2) no longer count as sample
  filtration, and subsampling counts as rarefying only when reads or sequencing depth are subsampled.
- Hygiene leaves out gels under UV light and the decontamination of a table of ASVs; library checks leave out
  Sanger sequencing.
- A syringe or filter unit used to filter the water is not the sampling device, unless the sentence says it
  collected the water.
- CTAB, Chelex and phenol-chloroform are methods, not kits: they give how the DNA was separated, not
  nucl_acid_ext_kit.
- samp_vol_we_dna_ext is always to check, as the volume filtered is the volume extracted only if the whole
  filter was.
- A sentence proposed for two descriptions is flagged.
- "Trimmomatic" no longer counts as trimming by its name alone; BLAST+ is named as BLAST+.
- A PCR programme written "with 35 subsequent cycles" is read, and the sentences after one about the second
  PCR, in its paragraph, describe the second PCR until one mentions the first PCR or its primer pairs.
- Page headers that give a journal's volume, pages, year and DOI are left out.

These changes were made after the held-out papers were seen, so the next set of papers will test them.

## Test set 2: 11 new papers, judged blind

Eleven papers published in 2025 and 2026, none seen before, tested the tool as it stood after the reviews
above (numbered 31 to 41). Only each paper's main PDF was read, as a user would usually have only the paper.
The set included a study with no eDNA in it (38), as a negative test, and two studies with targeted ddPCR
assays (39 and 41), the first test of the tool's targeted-assay mode.

**An independent reading.** Microsoft Copilot could not complete the reading, so each paper was read by a
separate Claude agent that had seen neither the tool, its rules nor its results, nor the earlier reviews. Each
agent had only the paper's PDF, the table of FAIRe terms and the instructions Copilot had been given
(`test_set_2_reader_instructions.md`), and read the PDF pages directly, not the text the tool extracts. Every
value needed a word-for-word excerpt: a script found 872 of the 886 excerpts in the paper's text, and the other
14 (table rows and symbols the PDF text garbles) were checked by hand. The reader also agreed with all 37
values Copilot had given in a first, partial pass.

**A blind review.** A person judged 453 pairs of paper and FAIRe term against the papers. The two values on
each row were shown as A and B, with the tool's value on a random side, and the key was kept out of the sheet.
The person judged every row where the values differed or only one was given, and 88 of the 214 rows where they
agreed (85 confirmed); agreed rows left unjudged count as right. Primer terms were left out.

| | Values given | Right | Partly right | Wrong |
|---|---|---|---|---|
| The tool | 244 | 220 (90%) | 9 (4%) | 15 (6%) |
| The independent reader | 435 | 409 (94%) | 11 (3%) | 15 (3%) |

The values for terms found reliably were right 93% of the time (124 of 134; 95% on the held-out papers) and
those to check 87% (96 of 110; 88%), so the two groups held up on new papers. All 10 values of the Mandatory
term pcr_0_1 were right, and all 33 values for the two ddPCR papers. Of the 431 values the papers give, the
tool found 220 (51%) and the reader 409 (95%): a reader of the whole paper finds far more, and the tool's
strengths are that it needs no AI service, gives the same answer every time and ties every value to its
sentence.

Most of the tool's 24 values that were not right fell into a few groups:

- The volume extracted (9 values): the tool gave the volume filtered, where the paper did not say how much of
  the filter was extracted.
- A PCR's cycles written as a word ("twenty cycles") were missed, so the second (indexing) PCR was taken for
  the first.
- Programs in the wrong role: Cutadapt as the demultiplexer in "Following demultiplexing, primers were trimmed
  using Cutadapt", DADA2 as the merge tool where identical ASVs were merged, BLAST from a sentence about
  Sanger sequencing of vouchered tissue.
- One value where the paper gives two (an NCBI and a custom database; sequencing in-house and at Azenta).
- A syringe for blood taken from birds as the eDNA sampling device; descriptions built from a sentence of
  another step (statistics, library preparation).
- In the paper with no eDNA, the tanks of "three 203-L collection tanks" as the sample size.

The reviewer also noted that some values repeat themselves, and that a syringe sometimes does take the sample.

### Changes made after test set 2

- Preprints' line numbers ("MATERIAL & METHODS 64") are removed, so the Methods heading is found and sentences
  are whole; bioRxiv's page footer is left out.
- A minus sign that a PDF's font does not map (a control character, or "/C0" in Wiley's PDFs) is read as a
  minus, and the outputs never carry a control character (it once stopped the review sheet).
- samp_vol_we_dna_ext is proposed only when the paper says the whole filter was extracted, or names the volume
  DNA was extracted from; otherwise a volume collected and filtered is proposed as samp_size.
- A text that never mentions DNA, PCR, primers or amplification gets no proposals, and a warning.
- A size before tank, bucket, carboy, cooler or aquarium is a container's size, not a sample's.
- Sentences about vouchered tissue, Sanger sequencing of references or blood are left out of the sample, PCR
  and bioinformatics rules (a sentence naming the DNeasy Blood & Tissue Kit is not).
- Each program is paired with the step named in its own clause ("dereplicated using vsearch and clustered
  using SWARM"), and a step named only as context ("Following demultiplexing, ...") is no step of the program.
  Merging counts only for reads or read pairs; "primers removed" counts as trimming.
- Software in a sentence about testing primers in silico (Primer-BLAST) is not the taxonomy method.
- Cycles written as words ("twenty", "eight") are read; a "terminal hold" is a final extension; a second PCR
  is recognised in "a second, five cycle, PCR" and in "The second PCR ... used the first PCR product"; a
  single-step PCR with indexing is one PCR; a capital S right after a number is a gene (18S), not seconds.
- Storage after filtering is recognised anywhere earlier in the sentence ("the filtrate ... was stored at").
- Statistics ("filtering those correlations with q values") are not sample processing.
- The vocabulary names BLAST, Azenta Life Sciences, SWARM, QuantStudio (Applied Biosystems) and Zymo's
  Quick-DNA kits as papers write them.

Measured against the 1,167 values judged in all three reviews, the changes drop 16 wrong and 10 partly right
values. Of the 43 right values no longer proposed exactly as before, 27 are still there in another form (BLAST
named as written, a program's version added, text without line numbers, a thermocycler moved from the second
PCR to the only PCR) or gave way to a more exact value. The other 16 are 8 volumes extracted and their units,
which the stricter rule leaves out because their papers do not say the whole filter was extracted; several now
come through as the volume collected. The judgments of test set 2 are in `reliability.tsv`, which moved the
demultiplexing, merging and BLAST-type programs and the sample size to the values to check, and the filter
diameter, inhibition check and the second PCR's master mix and programme to the reliable group.

## Files

- `run.sh OUTDIR [WEST_2024_TEXT]`: runs the tool on the development texts and, if given, the held-out
  paper.
- `make_testdata.py`: writes `tools/faire_mapper/test-data/method_details_reviewed.xlsx`, the review
  sheet for SEA-MES filled in as a person might, for the apply mapping test.
- `results/`: the values proposed for the development texts, and each run's summary.
- `test_set_2_reader_instructions.md`: the instructions each independent reader of test set 2 followed
  (with the table of FAIRe terms from the Copilot workbook).
