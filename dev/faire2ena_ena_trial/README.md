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

Submitted on 12 November 2026 through the test Webin Portal, with the chemistry fix: accepted
(ERS32843391 to ERS32843393).

The accepted XML shows a fault ENA did not refuse: the filter size (size_frac, 0.22 µm) went in as
"sizefraction upper threshold", with no unit. ENA's water checklist spells the label with a hyphen,
so ENA kept it as an extra attribute, and it defines the upper threshold as the pre-filter: the
filter that retains the sample is the lower threshold. The driver now writes it as
*size-fraction lower threshold* in µm (tool README, item 12). Rerun on the same three samples, the
sample XML differs from the accepted one only in that attribute.

## Experiments and runs (12 November 2026)

For the three 18S samples, with a new test study (PRJEB129763). In place of the real reads (already
public in ENA), six small made-up fastq.gz files of 100 read pairs each, with the same file names,
went to the Webin upload area through Windows File Explorer's FTP. A copy of the workbook was given
their MD5 checksums, and *FAIRe2ENA: experiments and runs* made the experiment and run XML from it
and the sample receipt, with instrument NextSeq 1000 (as ENA's run report gives for these runs).
The test Webin Portal's XML upload accepted all of it: three experiments (ERX17512955 to
ERX17512957) and three runs (ERR18120619 to ERR18120621). The test portal reads the same upload area.

## Wilderlab

Three Wilderlab-sequenced samples (M217, M251, M292) give clean sample XML, once the trial gives
their extraction volume its unit (mL, in `project_values_WL.tsv`). Their runs are single-end, which
FAIRe2ENA could not write until 12 November 2026 (tool README, item 13). The workbook has
lib_layout *single end*, but no file names yet, as the Wilderlab reads are not in ENA's run report
for the BioProject; a test of the runs needs their file names, or made-up ones.

## Still to do

- Try single-end runs on the test server, with Wilderlab file names (made-up reads will do).
- Find the cause of the 403 from the Webin REST service. The tools' help now leads with the
  Webin Portal's XML upload, which worked, and gives curl as the alternative.
