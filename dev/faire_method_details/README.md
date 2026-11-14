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

These held-out figures are provisional until the held-out rows have been checked by a person. Of the
tool's 91 held-out values that Copilot did not give, some are right and some are not.

## Files

- `run.sh OUTDIR [WEST_2024_TEXT]`: runs the tool on the development texts and, if given, the held-out
  paper.
- `make_testdata.py`: writes `tools/faire_mapper/test-data/method_details_reviewed.xlsx`, the review
  sheet for SEA-MES filled in as a person might, for the apply mapping test.
- `results/`: the values proposed for the development texts, and each run's summary.
