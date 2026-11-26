# FAIRe to Darwin Core

One Galaxy tool (`faire2dwc`) that turns a FAIRe workbook into a Darwin Core archive of presence
and absence records, for publishing to GBIF or OBIS through an IPT.

| Input | Output |
|---|---|
| FAIRe workbook (.xlsx); optional taxon table (TSV or CSV); dataset details for the EML | Darwin Core archive (zip: meta.xml, eml.xml, occurrence.txt, dna_derived_data.txt), the two tables and the EML on their own, and a report |

## Why this tool

None of the other FAIRe tools publishes qPCR or ddPCR results. GBIF's guide to publishing
DNA-derived data (Abarenkov et al. 2023, [doi:10.35035/doc-vf1a-nr22](https://doi.org/10.35035/doc-vf1a-nr22))
puts targeted species detection in its own category: occurrence records with the DNA derived data
extension, published through an IPT. GBIF's Metabarcoding Data Toolkit (FAIRe2MDT) and edna2obis
take metabarcoding data with read counts only. This tool covers the rest: targeted assays, and
metabarcoding data published as presence, such as a species-by-sample table with no sequences.

## Status

- Version 0.2.0 (24 November 2026) reads otuFinal_<assay>_<run> sheets, for an assay sequenced in
  several runs, with the run in each occurrenceID. Version 0.1.0 (23 November 2026) was written for
  the khapra beetle demonstration (`demo/khapra/`, `dev/faire_mapper_khapra/run.sh`), at Oliver
  Berry's request for a tool that
  makes it simple to publish presence and absence data to GBIF and OBIS.
- `planemo lint`: passes with no warnings. `flake8`: clean.
- `planemo test`: 5 of 5 tests pass in Galaxy 26.1.
- On the khapra beetle data: 162 records from four assay and machine combinations, with the 33
  controls left out. The archive has not been loaded into an IPT yet.

## How it works

`faire2dwc.py` reads projectMetadata (the FAIRe-ator layout, with assay1, assay2 ... columns named
by the assay_name row; the NOAA layout, with columns headed by assay names; or a single assay in
project_level), sampleMetadata, and ampData or otuFinal and taxaFinal.

**Targeted assays.** One record per sample and assay:

- *present* where detected_notDetected (or detected_notDetected_<assay>) is 1, *absent* where it is
  0. *Write absences* can be turned off;
- a blank value with ampData rows counts as detected when at least one replicate amplified, and the
  report says how many were worked out this way;
- a missing-value term (*missing: not provided*, *not applicable: ...*) means the sample is not
  written for that assay;
- the name comes from targetTaxonomicAssay for the assay;
- from ampData: the number of technical replicates that amplified and the mean Cq of those, in
  occurrenceRemarks and quantificationCycle; the mean copy number of all replicates, in
  estimatedNumberOfCopies and organismQuantity (with organismQuantityType *DNA copies (unit)*).

**Metabarcoding.** One record per sample and sequence with reads (or a 1) in otuFinal (or
otuFinal_<assay>, or otuFinal_<assay>_<run> for an assay sequenced in several runs), named from
taxaFinal. With several runs of one assay, the run goes into each occurrenceID. The columns of otuFinal can be samp_name or lib_id (mapped
to samples through experimentRunMetadata). Sequences with no taxon name are left out. The sequence
goes to DNA_sequence when it is a valid IUPAC sequence. Read counts are not published.

**Both.** Controls (samp_category other than *sample*) are always left out.

- occurrenceID is project_id, samp_name and assay (and seq_id), joined by underscores; eventID is
  project_id and samp_name; basisOfRecord is MaterialSample.
- country and locality come from geo_loc_name. countryCode comes from the country, or the form when
  the tool does not know the country. geodeticDatum is WGS84, as FAIRe asks.
- FAIRe's missing-value terms become empty cells; dates are written in ISO 8601.

`faire2dwc_terms.tsv` lists each Darwin Core term written, its URI, and the FAIRe term (or the
computed value) it comes from: 94 rows. The DNA derived data extension's URIs are as GBIF issued
it on 11 July 2024: MIxS terms at w3id.org/mixs, MIQE terms at rs.gbif.org/terms/miqe, and the
others at rs.gbif.org/terms.

**Taxon table.** An optional table with a *name* column (the name as the workbook gives it) and any
of scientificName, scientificNameID, taxonRank, kingdom to genus, and scientificNameAuthorship. OBIS
needs a WoRMS LSID (scientificNameID) for every name. With no taxon table, a taxaFinal taxonID with
a WoRMS database prefix becomes an LSID.

**EML.** The GBIF metadata profile 1.3: title, creator, metadata provider and contact, abstract,
keywords, licence, and geographic, temporal and taxonomic coverage from the records. With no name or
organisation on the form, the creator and contact come from project_contact (a name and email) and
institution in projectMetadata. The methods list each assay's target, gene, detection method and
detection criteria.

**Report.** Records written for each assay, the samples and controls left out, the columns written,
and what GBIF or OBIS will still want: eventDate, scientificName, countryCode, coordinates, kingdom,
scientificNameID (for OBIS), a licence and a creator.

## Decisions

- **Presence and absence, not read counts.** FAIRe2MDT and edna2obis already publish read counts,
  and the MDT is GBIF's route for them. This tool does what they do not.
- **Absences by default for targeted assays.** A targeted assay looks for one species, so a
  negative result is informative. The guide asks for occurrenceStatus *absent* for these.
- **A blank detected_notDetected falls back to ampData**, but a missing-value term does not: a
  person who wrote *missing: not provided* has said the result is not known.
- **Controls are never published.** A positive field control is a reason to read the records with
  care, and the help says so.
- **No name lookups.** The tool does not call WoRMS or GBIF, so it runs offline and gives the same
  result each time. The taxon table, or edna2obis's *match taxa*, gives the identifiers.
- **Licence.** GBIF takes CC0 1.0, CC BY 4.0 and CC BY-NC 4.0. The form can take the workbook's
  license or set one of these.

## Related tools and upstream notes

- edna2obis (`tools/edna2obis`) writes DNA derived data terms with `http://rs.gbif.org/terms/1.0/`
  URIs for all of them. The extension as GBIF issued it uses the MIxS, MIQE and GGBN URIs above.
  To raise with the edna2obis developers once confirmed against the IPT.
- FAIRe-fier's assay name check splits on the last underscore; see
  `tools/faire_mapper/README.md`.

## Before deployment on Galaxy Australia

- Load an archive into an IPT (GBIF's test IPT or the ALA's) and confirm the extension mapping and
  the EML.
- Try the OBIS route with a marine targeted dataset and WoRMS LSIDs.
- ToolShed owner `fair-edna` and maintainers in `<creator>`: done (23 November 2026).

## Files

| File | Purpose |
|---|---|
| `faire2dwc.py` | The tool |
| `faire2dwc.xml` | Galaxy tool definition |
| `faire2dwc_terms.tsv` | FAIRe to Darwin Core term mapping, with URIs |
| `faire_guide.xml` | The shared FAIRe tools guide, copied by `dev/faire_guide/sync.py` |
| `test-data/` | Test workbooks and taxon table, made by `dev/faire2dwc/make_test_data.py` |
| `LICENSE` | MIT |
| `.shed.yml` | ToolShed metadata (owner `fair-edna`) |

## Test data

Made-up values for real species, built by `dev/faire2dwc/make_test_data.py`:

- `targeted_two_assays.xlsx`: two qPCR assays for green crab (*Carcinus maenas*), CmaeCOI and
  CmaeND2; samples W1 to W4 and a field blank. W4 has *missing: not provided* for CmaeCOI and a blank
  for CmaeND2 (worked out from ampData). ampData has triplicates with *Undetermined* Cq values and
  copy numbers.
- `metabarcoding_presence.xlsx`: one MiFish assay, two samples and an extraction blank, three
  sequences (one with no name), and a project_contact for the EML.
- `metabarcoding_two_runs.xlsx`: the same, with the assay sequenced in two runs
  (otuFinal_MiFish_runA with P1; otuFinal_MiFish_runB with P2 and the blank).
- `taxa_carcinus.tsv`: the taxon table for green crab, with its WoRMS LSID.

## Tests

1. Targeted, with a taxon table, for GBIF and OBIS: 7 records, absences, replicate counts and the
   mean Cq in occurrenceRemarks, the control and the sample with a missing value left out.
2. One assay, no absences, for OBIS: the report lists the missing scientificNameID, kingdom and
   creator.
3. Metabarcoding presence: records and sequences, the unnamed sequence and the control column left
   out, and the creator and contact from project_contact.
4. One assay in two runs: the run in each occurrenceID.
5. An assay not in the workbook stops the tool.

Run them with `planemo test tools/faire2dwc/faire2dwc.xml`.
