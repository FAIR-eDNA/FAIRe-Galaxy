# Worked example: SEA-MES 18S data to ENA

Three seawater samples from CSIRO's SEA-MES eDNA survey, followed from the lab's own spreadsheet,
through the FAIRe tools in this repository, to a submission accepted by the European Nucleotide
Archive's test service: samples, study, experiments and runs.

> **This is a worked example, not a Galaxy run.** It uses real data (the SEA-MES data record, CC BY
> 4.0) and the same scripts the Galaxy tools wrap, run from the command line by
> `dev/faire_mapper_seames/run.sh` and the trial in `dev/faire2ena_ena_trial/`. In Galaxy, each step
> below is one tool form, and the files stay in the user's history. The submissions went to ENA's
> test service (`wwwdev.ebi.ac.uk`), which discards them within a day, so the accessions below no
> longer exist. The read files were small made-up stand-ins, as the real reads are already public.

| | |
|---|---|
| Data | SEA-MES 18S rRNA (V4) metabarcoding, 202 samples |
| Submitted | S001, S003 and S005 |
| When | 11 and 12 November 2026 |
| Where | ENA's test service, through the Webin Portal |

## The route

| Step | Galaxy tool, or where it happens | What it does |
|---|---|---|
| 1 | (the data record) | The lab's files |
| 2 | FAIRe mapper: propose mapping | Proposes a FAIRe term for each column |
| 3 | A person, in a spreadsheet | Reviews the proposals |
| 4 | FAIRe mapper: apply mapping | Writes the FAIRe workbook |
| 5 | FAIRe-fier | Checks the workbook against the FAIRe checklist |
| 6 | FAIRe2ENA: samples | Writes ENA's sample XML |
| 7 | ENA Webin Portal | Accepts the samples; registers a study |
| 8 | FTP | Puts the read files in the Webin upload area |
| 9 | FAIRe2ENA: experiments and runs | Writes ENA's experiment and run XML |
| 10 | ENA Webin Portal | Accepts the experiments and runs |

## One sample, end to end

Sample S001 was taken at 50 m off Flinders Island on 30 June 2023, from a Niskin bottle on RV
Investigator's CTD rosette (voyage IN2023_V05). Some of its values, as the lab recorded them, as
they sit in the FAIRe workbook, and as they went to ENA:

| Lab's column and value | FAIRe term and value | ENA attribute and value |
|---|---|---|
| Sample No. `S001` | `samp_name` S001 | sample alias S001 |
| Collection Date `30/06/2023` | `eventDate` 2023-06-30 | collection date 2023-06-30 |
| Latitude, Longitude `-40.577, 148.7301833` | `decimalLatitude`, `decimalLongitude` | geographic location (latitude) and (longitude), in DD |
| Locality `Flinders Island` | `geo_loc_name` Australia: Flinders Island | country Australia; region and locality Australia: Flinders Island |
| Depth (m) `50` | `minimumDepthInMeters`, `maximumDepthInMeters` 50 | depth 50 m |
| Temperature `14.1` | `temp` 14.1 (FAIRe: °C) | temperature 14.1 ºC |
| Salinity `35.49` | `salinity` 35.49 (FAIRe: psu) | salinity 35.49 psu |
| Volume filtered `2 L` | `samp_size` 2, `samp_size_unit` L | amount or size of sample collected 2 L |
| Filter pore size (µm) `0.22` | `size_frac` 0.22 (FAIRe: µm) | size-fraction lower threshold 0.22 µm |
| (project value) | `samp_store_temp` -80 (FAIRe: °C) | sample storage temperature -80 °C |
| (project value) | `env_medium` Seawater [ENVO:00002149] | environmental medium, the same |
| Oxygen `248.985` | `diss_oxygen` 248.985, unit not given | left out: ENA needs a unit |
| Nitrite `0.25` | `nitrite` 0.25, unit not given | left out: ENA needs a unit |
| (ENA run report) | `filename`, `filename2` and their MD5 checksums | experiment S001_18s and run S001_18s_run |

## Step 1. The lab's files

Everything starts from CSIRO's published data record for SEA-MES (Deagle et al. 2025). Nothing in
it is in FAIRe format. For 18S, three of its files were used (`demo/seames` holds a small copy):

- **The 18S ASV table**: the number of reads of each of 16,901 ASVs (rows) in each of 202 samples
  (columns), with each ASV's PR2 and SILVA lineage. Below the read counts sit 37 rows of sample
  details (depth, coordinates, date, temperature, oxygen and so on), one column per sample. A short
  script (`make_2L_table.py`) turns those rows into an ordinary sample table: 202 rows and 44
  columns, with the lab's own column names.
- **ENA's run report** for the SEA-MES BioProject (PRJNA1263580): each library's name, fastq file
  names and MD5 checksums.
- **The methods**, from the project's final report: primers, PCR, sequencing and bioinformatics.

## Step 2. Propose mapping

*Galaxy tool: FAIRe mapper: propose mapping*

The mapper takes the sample table from step 1. It compares each column's name and values with the
FAIRe checklist and proposes a FAIRe term, with its reasons and a score from 0 to 1. It accepts a
match that scores well and is clearly ahead of the other candidates, and sends the rest to a person
to review. It works by rules, so the same table always gives the same proposals. (A separate tool,
*FAIRe mapper: ask a language model*, can give a second opinion on the columns for review. It was
not used here.)

Of the 44 columns, 20 were accepted, 5 went to review and 19 had no FAIRe term. Some examples:

| Column | Proposed term | Score | Mapper's call | Mapper's reasoning (shortened) |
|---|---|---|---|---|
| Collection Date | `eventDate` | 1.00 | accept | Header matches 'collection date'. Dates written dd/mm/yyyy, so convert them to ISO 8601. |
| Depth (m) | `minimumDepthInMeters`, `maximumDepthInMeters` | 1.00 | accept | Header matches 'depth'; numbers from 5 to 530. One depth for each sample fills both terms. |
| Latitude | `decimalLatitude` | 1.00 | accept | Decimal degrees within the latitude range (-42.165 to -36.367). |
| Volume filtered | `samp_size`, `samp_size_unit` | 0.98 | accept | Values such as '2 L' split into a number and a unit. |
| Sterivex Number | `input_read_count` | 0.45 | review | Header partly matches 'number read'; numbers 1 to 156. |
| Nominal depth | `tot_depth_water_col` | 0.48 | review | Header partly matches 'total depth'; numbers 5 to 530. |
| Phosphate | none | n/a | no match | FAIRe has no term for phosphate, so the column is kept as a user-defined field. |

Since version 0.6.1 (13 November 2026), *Depth (m)* and *Nominal depth* would both go to review,
however strong the match. FAIRe's sampling depth terms and `tot_depth_water_col` are often confused,
so the comment names them, says what each means, and asks whether the column is the depth the sample
was taken from or the depth of the water at the site.

Since version 0.7.0, a column with no FAIRe term gets a MIxS or Darwin Core term whose name matches,
for review, as the FAIRe guidelines ask. In this table, *Phosphate*, *Silicate* and *Pressure* get
MIxS's phosphate, silicate and pressure, and *Ammonia* gets MIxS's ammonium, which is close but not
the same name. Once a reviewer confirms one, apply mapping names the user-defined field after the
term. The other 14 columns with no FAIRe term (Voyage, CTD #, Hours from noon and so on) get none.

## Step 3. Review

*A person, in a spreadsheet*

Someone who knows the data checks the proposals. Here, seven were deleted (all five marked for
review, and two the mapper had accepted) and one was added.

In Galaxy, the review is currently done in a spreadsheet. The reviewer downloads the crosswalk that
propose mapping writes, edits it in Excel or similar, and uploads it again for apply mapping. To
confirm a match marked for review, they change its `skos:closeMatch` to `skos:exactMatch`; to stop
a column being matched, they delete its row. The tools don't yet offer a more interactive way to
review. For this example, each decision went into a small table of column, action and reason
(`dev/faire_mapper_seames/reviewer_decisions_18S.tsv`), and a short script (`review.py`) applied it
to the crosswalk, so the review is on record.

| Column | Decision | Reason |
|---|---|---|
| Sample | delete | The fastq name of each sample (S001_S13_L001), not the sample material. |
| Sterivex Number | delete | The number of the filter cartridge, not a read count. |
| Sample ID | delete | A field label for each sample (SM1_CTD001_Bottom_a), not a material sample ID. |
| Location | delete | Station codes, such as S2.1 (Flinders MP). Locality gives geo_loc_name on its own. |
| Filtration Date | delete | The date of filtering, not the date the record changed. |
| Filtered by | delete | Who filtered the water. Collected by gives recordedBy. |
| Nominal depth | delete | The planned sampling depth, not the depth of the water column. |
| Collected by | add `recordedBy` | The people who collected the samples. |

## Step 4. Apply mapping

*Galaxy tool: FAIRe mapper: apply mapping*

The reviewed crosswalk, a short list of project-wide values (`project_values_18S.tsv`) and the ASV
table go in. A FAIRe workbook in FAIRe-ator's layout comes out, with a log of every change: 202
samples, 54 FAIRe terms filled, 25 lab columns kept as user-defined fields, and 16,901 sequences in
otuFinal and taxaFinal.

- **Values converted:** '30/06/2023' became 2023-06-30; '2 L' became 2 and L; 'Flinders Island'
  became 'Australia: Flinders Island'.
- **Project values** from the methods: target gene 18S V4, the primers TAReuk454FWD1 and the
  modified TAReuk-Rev3 with their sequences, sequencing at the Ramaciotti Centre on a NextSeq 1000,
  SILVA v138.1 and PR2 v5.0.0, and the ENVO terms for seawater.
- **Libraries:** ENA's run report gave a library for each of the 202 samples, with both fastq names
  and checksums. Fifteen other 18S libraries, such as a mock community and samples not in the ASV
  table, were left out and listed. Six of them are controls sequenced with the samples: a
  no-template control (a PCR negative), a mock community (ATCC1010) and a soil sample on each of the
  two runs. They have reads at the archive but are not in the ASV table. Since 13 November 2026 the
  sample table has a row for each (`make_2L_table.py`, given the run report), with its sample type
  and control type, so the workbook has 208 samples, six of them controls, and only the nine 2 L
  samples with no details in the record are left out.
- **Taxonomy:** PR2 lineages, with 1,057 sequences named to species and 1,894 to genus. The SILVA
  lineages are kept in identificationRemarks.

## Step 5. Check the workbook

*Galaxy tool: FAIRe-fier*

FAIRe-fier, CSIRO's FAIRe validator, checks every value against the checklist.

- **sampleMetadata passes.** Its warnings point out the 25 extra lab columns, such as Phosphate and
  Pressure, and suggest giving coordinates to at least five decimal places.
- **projectMetadata passes** with FAIRe mapper 0.5.1, which writes the checklist version as 1. With
  0.5.0, FAIRe-fier reported one error here: the workbook gave the checklist's file name, as
  FAIRe-ator writes it, and FAIRe-fier expects a number.

## Step 6. Samples

*Galaxy tool: FAIRe2ENA: samples*

FAIRe2ENA writes ENA's sample XML, on ENA's water checklist (ERC000024), with the taxon for marine
metagenomes (408172). For the test, the workbook was cut to three samples: S001, S003 and S005.

ENA wants numbers such as temperature as plain numbers with a unit. The Galaxy tool adds FAIRe's
units, and leaves out any value it can't give a unit. It lists those in its log:

```
INFO: 'dissolved oxygen' left out for 3 sample(s), as ENA needs a number with a unit and diss_oxygen_unit is empty: S001, S003, S005
INFO: 'nitrite' left out for 3 sample(s), as ENA needs a number with a unit and nitrite_unit is empty: S001, S003, S005
INFO: wrote 3 sample(s) for project SEA-MES_eDNA with taxon 408172
```

The SEA-MES sources don't state the units of oxygen and nitrite. Once they're known, filling
`diss_oxygen_unit` and `nitrite_unit` in the workbook brings both back.

<details>
<summary>Part of S001's sample XML</summary>

```xml
<SAMPLE alias="S001" center_name="CSIRO">
  <SAMPLE_NAME><TAXON_ID>408172</TAXON_ID></SAMPLE_NAME>
  <SAMPLE_ATTRIBUTE><TAG>collection date</TAG><VALUE>2023-06-30</VALUE></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>geographic location (latitude)</TAG><VALUE>-40.577</VALUE><UNITS>DD</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>depth</TAG><VALUE>50</VALUE><UNITS>m</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>temperature</TAG><VALUE>14.1</VALUE><UNITS>ºC</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>salinity</TAG><VALUE>35.49</VALUE><UNITS>psu</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>amount or size of sample collected</TAG><VALUE>2</VALUE><UNITS>L</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>size-fraction lower threshold</TAG><VALUE>0.22</VALUE><UNITS>µm</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>sample storage temperature</TAG><VALUE>-80</VALUE><UNITS>°C</UNITS></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>environmental medium</TAG><VALUE>Seawater [ENVO:00002149]</VALUE></SAMPLE_ATTRIBUTE>
  <SAMPLE_ATTRIBUTE><TAG>ENA-CHECKLIST</TAG><VALUE>ERC000024</VALUE></SAMPLE_ATTRIBUTE>
  ...
</SAMPLE>
```

The tool writes each element on its own line; it is shortened here.

</details>

## Step 7. Samples and study

*ENA Webin Portal (test service)*

In the Webin Portal's *Submit XMLs* page, the sample XML went in with the submission file the tool
also writes (action ADD). ENA checked every attribute against the water checklist and accepted all
three samples (test accessions ERS32843391 to ERS32843393). The receipt it returned, with these
accessions, was saved as a file for step 9. A study then came from the portal's *Register study*
form (PRJEB129763), for the experiments to point to.

## Step 8. Read files

*FTP to the Webin upload area*

ENA accepts a run only when its fastq files are in the submitter's upload area, with checksums that
match. The real SEA-MES reads are already public, so for this test each of the six files (two per
sample) was replaced by a small made-up file with the same name: 100 read pairs of invented
sequence, about 6 KB each. A copy of the workbook was given their checksums.

The six files went to the Webin upload area through Windows File Explorer's FTP connection. The
test service reads the same upload area as the real one.

## Step 9. Experiments and runs

*Galaxy tool: FAIRe2ENA: experiments and runs*

The second FAIRe2ENA tool reads ENA's sample receipt, so each experiment points to the right sample
accession, and the workbook's library rows, for the file names and checksums. The study accession
and the sequencer (NextSeq 1000) are set on the tool's form. The library layout comes from
`lib_layout` in the workbook: here *paired end*, so each run has two files.

<details>
<summary>S001's experiment and run</summary>

```xml
<EXPERIMENT alias="S001_18s" center_name="CSIRO">
  <TITLE>S001_18s</TITLE>
  <STUDY_REF accession="PRJEB129763"/>
  <DESIGN>
    <DESIGN_DESCRIPTION>eDNA metabarcoding</DESIGN_DESCRIPTION>
    <SAMPLE_DESCRIPTOR accession="ERS32843391"/>
    <LIBRARY_DESCRIPTOR>
      <LIBRARY_NAME>S001_18s</LIBRARY_NAME>
      <LIBRARY_STRATEGY>AMPLICON</LIBRARY_STRATEGY>
      <LIBRARY_SOURCE>METAGENOMIC</LIBRARY_SOURCE>
      <LIBRARY_SELECTION>PCR</LIBRARY_SELECTION>
      <LIBRARY_LAYOUT><PAIRED/></LIBRARY_LAYOUT>
    </LIBRARY_DESCRIPTOR>
  </DESIGN>
  <PLATFORM><ILLUMINA><INSTRUMENT_MODEL>NextSeq 1000</INSTRUMENT_MODEL></ILLUMINA></PLATFORM>
</EXPERIMENT>

<RUN alias="S001_18s_run" center_name="CSIRO">
  <EXPERIMENT_REF refname="S001_18s"/>
  <DATA_BLOCK><FILES>
    <FILE filename="SRR33983413_1.fastq.gz" filetype="fastq" checksum_method="MD5" checksum="5651edb6ff5a6e029b77a35d2af187e9"/>
    <FILE filename="SRR33983413_2.fastq.gz" filetype="fastq" checksum_method="MD5" checksum="161a64c30fbb2ee30e45d0ecf6dcd8e1"/>
  </FILES></DATA_BLOCK>
</RUN>
```

The checksums are those of the made-up stand-in files.

</details>

## Step 10. Experiments and runs accepted

*ENA Webin Portal (test service)*

The experiment, run and submission files went in together through the same *Submit XMLs* page, and
ENA accepted them: three experiments (ERX17512955 to ERX17512957) and three runs (ERR18120619 to
ERR18120621). That completed the chain for all three samples.

## What the trials changed

ENA's checks found problems the tools' own tests had missed. Each was fixed in the Galaxy driver,
without changing the FAIRe2ENA scripts, with a test written first
(`tools/faire2ena/README.md`, items 11 to 14).

- **11 November, 16S samples.** The first test submission, of three SEA-MES 10 L samples (M001 to
  M003), was refused. FAIRe2ENA left out the units ENA requires for temperature, salinity, storage
  temperature and extraction volume, and wrote "Unknown" for the empty sample size. With the units
  fix, ENA accepted the same samples that day.
- **12 November, 18S samples.** The oxygen and nitrite fields had the same fault, and the fix was
  extended to the chemistry fields.
- **After the 18S submission.** The accepted XML showed one more fault, which ENA did not refuse:
  the filter size went in as "sizefraction upper threshold", with no unit. ENA's checklist spells
  the label with a hyphen and defines the upper threshold as the pre-filter; the filter that retains
  the sample is the lower threshold. The tool now writes it as above.

S001 as the FAIRe2ENA script writes it, and as the Galaxy tool writes it now:

| ENA attribute | FAIRe2ENA script | Galaxy tool |
|---|---|---|
| temperature | 14.1, no unit | 14.1 ºC |
| salinity | 35.49, no unit | 35.49 psu |
| sample storage temperature | -80, no unit | -80 °C |
| amount or size of sample collected | "2 L", unit L | 2 L |
| dissolved oxygen | 248.985, no unit, plus a second copy, *dissolved_oxygen*, "Unknown" | left out, listed in the log |
| nitrite | "Unknown" | left out, listed in the log |
| size fraction | *sizefraction upper threshold* 0.22, no unit | *size-fraction lower threshold* 0.22 µm |

## Not covered yet

- **Real reads.** The runs used made-up files. Submitting a real dataset's reads is still to do.
- **Single-end runs.** FAIRe2ENA's run tool writes single-end runs since 12 November 2026 (for
  Wilderlab data), but they have not yet been tried on ENA's test service.
- **Submitting from the command line.** ENA's REST service refused the test account with HTTP 403,
  for reasons not yet known. The Webin Portal's XML upload worked, and the tools' help now leads
  with it.
- **Galaxy itself.** These steps ran the scripts the Galaxy tools wrap, from the command line. In
  Galaxy each step is one tool form, and the files stay in the user's history.

## Sources

- Data: Deagle B. et al. (2025) [Environmental DNA data from the RV Investigator South-East
  Australian Marine Ecosystem Survey (SEA-MES) voyages (IN2023_V05 and IN2024_V03)](https://doi.org/10.25919/ngqx-3557).
  CSIRO Data Access Portal, CC BY 4.0. Reads: NCBI BioProject
  [PRJNA1263580](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1263580/).
- ENA checklist: [ERC000024 (GSC MIxS water)](https://www.ebi.ac.uk/ena/browser/view/ERC000024).
- The trial: `dev/faire2ena_ena_trial/README.md`; the SEA-MES runs: `dev/faire_mapper_seames/README.md`.
