# FAIRe2ENA on ENA's test server

A trial of submitting samples made by *FAIRe2ENA: samples* to ENA's test service
(`wwwdev.ebi.ac.uk`), which checks a submission as the real service does and discards it within a
day.

## Samples

Three 10 L samples of the SEA-MES record (M001 to M003; `dev/faire_mapper_seames`), from the
workbook the SEA-MES trial writes, with checklist ERC000024 (water) and centre name CSIRO.

**8 November 2026.** The test Webin Portal refused an XML upload with "Webin submission service
failed", before checking the files, probably because the Webin account had been made that day.

**11 November 2026.** With curl, the Webin REST service (`/ena/submit/drop-box/submit/`, test and
real) answered HTTP 403 with an empty reply, from a Windows computer, whatever password was given.
The same account logged in to the Webin Portal, and an XML upload there reached ENA's checks. The
cause of the 403 is not yet known.

ENA refused the three samples, for two reasons:

| Attribute | ENA's message | Cause |
|---|---|---|
| temperature, salinity, sample storage temperature, sample volume or weight for DNA extraction | must have required property 'unit' | FAIRe2ENA writes no UNITS for them; the SEA-MES workbook also had no samp_vol_we_dna_ext_unit |
| amount or size of sample collected | must match pattern (a plain number) | samp_size is empty, but FAIRe2ENA treats the empty cell as filled and writes "Unknown" |

Everything else passed: dates, coordinates, depth, environment terms, country.

## Fixes

- The Galaxy driver adds ENA's units and plain numbers (`tools/faire2ena/README.md`, item 11), with
  units from ENA's checklist ERC000024 (read on 11 November 2026) and FAIRe's units from the FAIRe
  checklist v1.0.2. Tests 1 and 4 of `faire2ena_sample.xml` cover it; `make_testdata.py` here writes
  the test workbook for test 4.
- The SEA-MES trial gives the 10 L samples' extraction volume its unit (`samp_vol_we_dna_ext_unit`
  mL in `dev/faire_mapper_seames/project_values.tsv`): 10000 mL, as these are 10 L samples.

With both, the three samples carry units for all five attributes, and no "Unknown".

**Resubmitted 11 November 2026** through the test Webin Portal: accepted. ENA gave the three
samples test accessions (ERS32837772 to ERS32837774, submission ERA37798767), which the test
service discards within a day.

## 18S samples (12 November 2026)

Three 2 L samples of the SEA-MES 18S set (S001, S003, S005) carry dissolved oxygen and nitrite,
which FAIRe2ENA wrote without units or as "Unknown", like the fields above. Item 11 of the tool
README now covers the chemistry fields too. The 18S sources give no units for oxygen and nitrite, so
the samples go to ENA without them, and FAIRe2ENA's log lists them.

## Still to do

- Experiments and runs, from the sample receipt (*FAIRe2ENA: experiments and runs*). Runs need
  the fastq files in the test upload area.
- Find the cause of the 403 from the Webin REST service, which the tool's help describes for
  submitting.
