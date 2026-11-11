# Related tools: edna2dwc

[intertidalagency/edna2dwc](https://github.com/intertidalagency/edna2dwc) (MIT, alpha; read at
commit `a0b6b32`, 1 November 2026) builds Darwin Core Archives for GBIF and OBIS from eDNA results:
spreadsheets, QIIME 2 artifacts, BIOM tables, phyloseq objects and methods documents. It was
reviewed from its documentation and code; it was not run here.

## How it compares

| | edna2dwc | FAIRe Galaxy tools |
|---|---|---|
| Output | Darwin Core Archive (occurrence core, DNA-derived data and measurement extensions, EML) | FAIRe workbook, then ENA, NCBI, QIIME 2 (and OBIS/GBIF through edna2obis) |
| Where it runs | command line, driven by an AI coding agent through a skill | Galaxy tools; the model steps are optional scripts |
| Role of the AI | the agent writes a script that reads the user's files into one table, finds metadata in documents, and talks the user through each decision | the model answers the mapper's review requests and finds values in the methods text; code checks every answer |
| Column mapping | exact name, then case-insensitive, then a curated alias list; two columns for one term are flagged | header words plus a profile of the values (types, formats, vocabularies), one term per column, routed to accept, review or no match |
| Missing values | left blank and reported; never filled | left out and listed as mandatory terms not covered |
| Who decides | every answer is `{value, provenance, confirmed}`; only a person's words go in `confirmed`; the build waits at `needs_review` until then | answers from a person are *confirmed*; answers from a model are now marked *model* (see below) |
| Checking | a separate agent audits every published value against the sources ("fabrication audit") | quotes from the methods must appear in the text; model answers must be one of the candidates |
| Taxonomy | resolves names against WoRMS and the GBIF backbone | not covered yet |
| Reproducibility | `reproduce/` folder and `replay` command | Galaxy histories and workflows |

The two overlap in purpose (turning a laboratory's own files into standard records) but not in
output. edna2dwc goes straight to Darwin Core and does not produce FAIRe, SRA or ENA metadata.
Its DNA-derived data terms (`target_gene`, `pcr_primer_forward` and so on) have the same names as
FAIRe's, so a FAIRe workbook made by these tools should map onto them almost entirely by exact
name; that is untested.

## What we took from it

- **A model is not a reviewer.** The mapper used to mark every answer in the answers file as
  *confirmed* and write it to the crosswalk as manual curation, whoever gave it. Answers can now
  say who gave them (`"by": "model:<name>"`, set by `faire_mapper_adjudicate.py`); those columns
  are routed *model*, with the note "not yet checked by a person", and only a person's answers are
  *confirmed*.

## Ideas worth adopting later

1. **Provenance on every value.** Each value in the planned transform step (sample sheet to FAIRe
   workbook) could carry where it came from: the column, the methods quote, the primer table row,
   or the person who supplied it. The methods step already records quotes.
2. **An independent audit at the end.** A second model, given only the sources and the finished
   FAIRe workbook, lists values it cannot trace. This was done by hand for the Dryad trial.
3. **Plain reports of what is missing**, written to pass on with the data (their
   `CONVERSION_REPORT.md`), alongside the list of mandatory terms not covered.
4. **Taxonomy checks** against WoRMS and GBIF for the FAIRe taxa sheets, unless the Galaxy eDNA lab
   already has tools for this.

## Worth discussing with its authors

- Whether edna2dwc could read FAIRe workbooks directly, so that FAIRe data made in Galaxy can go to
  OBIS and GBIF through either edna2dwc or edna2obis.
- Sharing the alias list for column headers and the primer and unit tables, so the tools do not
  maintain separate lists.
