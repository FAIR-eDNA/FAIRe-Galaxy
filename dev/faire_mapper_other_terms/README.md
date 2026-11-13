# MIxS and Darwin Core terms for FAIRe mapper

`build_terms.py` writes `tools/faire_mapper/mixs_dwc_terms.tsv`, the MIxS and Darwin Core terms that
the FAIRe checklist does not have. Propose mapping suggests one of them, for review, for a column
with no FAIRe term, as the FAIRe guidelines ask for a MIxS or Darwin Core term before a made-up name.
Apply mapping names the column after a term the reviewer confirms.

## Sources

| Standard | Version | Licence | File read |
|---|---|---|---|
| MIxS, Genomic Standards Consortium | v7.0.1 (release tag) | CC0 1.0 | `src/mixs/schema/mixs.yaml` from https://github.com/GenomicsStandardsConsortium/mixs |
| Darwin Core, TDWG | `master` at commit 7678044 (5 November 2026) | CC BY 4.0 | `vocabulary/term_versions.csv` from https://github.com/tdwg/dwc |

The TSV keeps the terms' names, identifiers, labels and definitions as published, with an
attribution line for each standard at its top. The selection and the `kind` and `scope` columns are
FAIRe mapper's.

## What is kept

- **MIxS** (745 terms): the slots used by a MIxS checklist or extension (environmental package),
  not deprecated. `kind` is *number* when MIxS writes the value as a number and a unit
  (0.7 micromole per liter); `unit` is MIxS's preferred unit; `scope` lists the extensions, or the
  checklists when no extension uses the slot.
- **Darwin Core** (95 terms): the recommended Simple Darwin Core terms in the dwc namespace from the
  record-level, Event, Location and MaterialEntity groups. The Occurrence, Organism, Identification,
  Taxon and GeologicalContext groups describe specimens and observations, not samples, and are left
  out.
- **Left out of both**: terms the FAIRe checklist has, by name or by IRI (its URI column), and MIxS
  lat_lon and depth, which FAIRe splits into decimalLatitude and decimalLongitude, and
  minimumDepthInMeters and maximumDepthInMeters.

## Rebuilding

Clone each repository into its own empty folder (downloaded files are untrusted: nothing from them is
run), then:

```bash
git clone --depth 1 --branch v7.0.1 https://github.com/GenomicsStandardsConsortium/mixs.git /tmp/mixs
git clone --depth 1 https://github.com/tdwg/dwc.git /tmp/dwc
python -I dev/faire_mapper_other_terms/build_terms.py /tmp/mixs/src/mixs/schema/mixs.yaml \
    /tmp/dwc/vocabulary/term_versions.csv tools/faire_mapper/checklist/FAIRe_checklist_v1.0.2.xlsx \
    tools/faire_mapper/mixs_dwc_terms.tsv v7.0.1 "$(git -C /tmp/dwc log -1 --format=%h)"
```

Rebuild it when FAIRe, MIxS or Darwin Core changes, and update the versions above and in the tool
help.

## How the mapper uses it

For a column with no FAIRe match (not a unit column, not empty, and not answered by a reviewer or
model), the mapper scores these terms the same way as FAIRe terms, and suggests the best one when:

- every word of the column's name matches a word of the term's name or label, or is a common word
  such as *sample*: *Sample year* fits Darwin Core's year, but *Field bottle number* does not fit
  fieldNumber, nor *Field sheet page* MIxS's field;
- the name match is at least 0.75 both ways, and the values do not rule the term out.

On the trial tables (13 November 2026) this suggested terms for these columns only:

| Table | Column | Term |
|---|---|---|
| SEA-MES 18S | Phosphate, Silicate, Pressure | MIxS phosphate, silicate, pressure |
| SEA-MES 18S | Ammonia | MIxS ammonium (close, for the reviewer to judge) |
| GOMECC (benchmark) | ammonium, phosphate, pressure, silicate | the MIxS terms of the same names |
| Van der Heyde (Dryad) | Sample_year | Darwin Core year |

The other benchmark, Dryad and Australian tables got none.
