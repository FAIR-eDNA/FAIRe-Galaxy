# Worked example: SEA-MES 18S data to ENA

Three seawater samples from CSIRO's SEA-MES eDNA survey, followed from the lab's own files, through
the FAIRe tools in this repository, to a submission accepted by the European Nucleotide Archive's
test service: samples, study, experiments and runs. The FAIRe workbook is built from several inputs:
the lab's sample details, its ASV table, ENA's run report, values for the whole project and a
reviewer's decisions (*What goes in*, below). Other labs will have other files, in other layouts;
these are the ones SEA-MES published.

> **This is a worked example, not a Galaxy run.** It uses real data (the SEA-MES data record, CC BY
> 4.0) and the same scripts the Galaxy tools wrap, run from the command line by
> `dev/faire_mapper_seames/run.sh` and the trial in `dev/faire2ena_ena_trial/`. In Galaxy, each step
> below is one tool form, and the files stay in the user's history. The submissions went to ENA's
> test service (`wwwdev.ebi.ac.uk`), which discards them within a day, so the accessions below no
> longer exist. The read files were small made-up stand-ins, as the real reads are already public.

| | |
|---|---|
| Data | SEA-MES 18S rRNA (V4) metabarcoding, 202 samples and 6 controls |
| Inputs | ASV table with sample details, ENA's run report, the methods, project values, review decisions |
| Submitted | S001, S003 and S005 |
| When | 11 and 12 November 2026; steps 1 to 5 updated for FAIRe mapper 0.7.3 on 13 November |
| Where | ENA's test service, through the Webin Portal |

## The route

| Step | Galaxy tool, or where it happens | What it does |
|---|---|---|
| 1 | (the data record) | The lab's files |
| 2 | FAIRe mapper: propose mapping | Proposes a FAIRe term for each column |
| 3 | A person, in the review sheet | Reviews the proposals |
| 4 | FAIRe mapper: apply mapping | Writes the FAIRe workbook |
| 5 | FAIRe-fier | Checks the workbook against the FAIRe checklist |
| 6 | FAIRe2ENA: samples | Writes ENA's sample XML |
| 7 | ENA Webin Portal | Accepts the samples; registers a study |
| 8 | FTP | Puts the read files in the Webin upload area |
| 9 | FAIRe2ENA: experiments and runs | Writes ENA's experiment and run XML |
| 10 | ENA Webin Portal | Accepts the experiments and runs |

## What goes in

Each output is built from these inputs. Three come from the published data record and ENA; two come
from people, and would come from any lab using the tools. Which files a lab has, and their layouts,
differ from lab to lab: separate OTU and taxonomy tables, a sample sheet, a sequencing facility's run
sheet. *FAIRe mapper: identify your files* says what each file looks like and which step it goes to.

| Input | Where it came from | What it gives | Used in |
|---|---|---|---|
| 18S ASV table (data record file 7) | The lab, published | Read counts of 16,901 ASVs in 202 samples, with PR2 and SILVA lineages; below them, 37 rows of sample details, which a short script turns into the sample table | Steps 1, 2, 4 |
| ENA's run report for PRJNA1263580 | ENA, downloaded | Each library's name, fastq files and MD5 checksums, and the six control libraries sequenced with the samples | Steps 1, 4, 9 |
| The methods (the project's final report) | The lab, published | Primers, PCR, sequencing, storage and bioinformatics, read by *find primers* and by a person | Step 4, through the project values |
| Values for the whole project (`project_values_18S.tsv`) | A person, from the methods and the 10 L samples' BioSample sheet | Project terms no table holds: project name and contact, primers, protocols, env_medium, storage temperature | Step 4 |
| The reviewer's decisions | A person, in the review sheet | Accept, Reject or Change for each column of the sample table | Steps 3, 4 |
| Tool settings | A person, on each tool's form | Sample type, assay, the sites' UTC offset; for ENA, the centre name, taxon, study accession and sequencer | Steps 2, 4, 6, 9 |
| ENA's sample receipt | ENA, after step 7 | The sample accessions, so each experiment points to its sample | Step 9 |

The FAIRe workbook (step 4) is the one file every later step reads: FAIRe-fier checks it, and both
FAIRe2ENA tools convert it.

## One sample, end to end

Sample S001 was taken at 50 m off Flinders Island on 30 June 2023, from a Niskin bottle on RV
Investigator's CTD rosette (voyage IN2023_V05). Some of its values, as the lab recorded them, as
they sit in the FAIRe workbook, and as they went to ENA:

| Lab's column and value | FAIRe term and value | ENA attribute and value |
|---|---|---|
| Sample No. `S001` | `samp_name` S001 | sample alias S001 |
| Collection Date `30/06/2023`, Collection Time (UTC) `08:06` | `eventDate` 2023-06-30T18:06+10:00 (local time) | collection date 2023-06-30T18:06+10 (the trial sent 2023-06-30; see step 6) |
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

Everything starts from CSIRO's published data record for SEA-MES (Deagle et al. 2025) and ENA's
report of its reads. Nothing in them is in FAIRe format. For 18S, three files were used
(`demo/seames` holds a small copy), with two inputs from people:

- **The 18S ASV table**: the number of reads of each of 16,901 ASVs (rows) in each of 202 samples
  (columns), with each ASV's PR2 and SILVA lineage. Below the read counts sit 37 rows of sample
  details (depth, coordinates, date, temperature, oxygen and so on), one column per sample. A short
  script (`make_2L_table.py`) turns those rows into an ordinary sample table with the lab's own
  column names, and adds a row for each of the six controls sequenced with the samples (from ENA's
  run report): 208 rows and 47 columns.
- **ENA's run report** for the SEA-MES BioProject (PRJNA1263580): each library's name, fastq file
  names and MD5 checksums.
- **The methods**, from the project's final report: primers, PCR, sequencing and bioinformatics.
- **From people**: the values for the whole project, typed from the methods and the 10 L samples'
  BioSample sheet (`project_values_18S.tsv`), and the reviewer's decisions (step 3).

## Step 2. Propose mapping

*Galaxy tool: FAIRe mapper: propose mapping*

The mapper takes the sample table from step 1. It compares each column's name and values with the
FAIRe checklist and proposes a FAIRe term, with its reasons and a score from 0 to 1. It accepts a
match that scores well and is clearly ahead of the other candidates, and sends the rest to a person
to review. It works by rules, so the same table always gives the same proposals. (A separate tool,
*FAIRe mapper: ask a language model*, can give a second opinion on the columns for review. It was
not used here.)

Of the 47 columns, the mapper accepted 22, sent 11 to review and found no term for 14. Some
examples, as they appear in the review sheet (step 3):

| Input term | Proposed term | Score | Mapper's call | Mapper's reasoning (shortened) |
|---|---|---|---|---|
| Collection Date | `eventDate` | 1.00 | accept | The column name matches 'collection date'. Dates written dd/mm/yyyy, converted to ISO 8601. |
| Latitude | `decimalLatitude` | 1.00 | accept | Decimal degrees within the latitude range (-42.165 to -36.367). |
| Filtered by | `recordedBy` | 0.97 | accept | The column name matches 'filtered by'. One value (Sahan) for the whole table. |
| Depth (m) | `minimumDepthInMeters` + `maximumDepthInMeters` | 1.00 | review | A strong match, sent to review because these terms and `tot_depth_water_col` are often confused. |
| Volume filtered | `samp_size` + `samp_size_unit` | 0.97 | review | Values such as '2 L' split into a number and a unit; often confused with `samp_vol_we_dna_ext`. |
| Nominal depth | `tot_depth_water_col` | 0.48 | review | The column name partly matches 'total depth'; numbers 5 to 530. |
| Sterivex Number | `input_read_count` | 0.45 | review | The column name partly matches 'number read'; numbers 1 to 156. |
| Phosphate | `phosphate` (MIxS term) | 1.00 | review | No FAIRe term fits, so the MIxS term of the same name, as the FAIRe guidelines ask. |

FAIRe's sampling depth terms and `tot_depth_water_col` are often confused, as are `samp_size` and
`samp_vol_we_dna_ext`, so the mapper always sends them to review, however strong the match, and its
reasoning names the other terms, says what each means and asks which the column holds.

For a column with no FAIRe term, the mapper looks for a MIxS or Darwin Core term whose name matches,
as the FAIRe guidelines ask. Here *Phosphate*, *Silicate* and *Pressure* get MIxS's phosphate,
silicate and pressure, and *Ammonia* gets MIxS's ammonium, which is close but not the same name. The
other 14 columns (Voyage, CTD #, Hours from noon and so on) get none, and are kept as the lab's own
terms (user-defined fields).

Propose mapping also lists *additional checks to make*: here, that the collection times are in UTC
(the workbook gives local time, so the UTC offset is needed) and the often confused terms.

## Step 3. Review

*A person, in the review sheet*

Propose mapping writes a **review sheet**, an Excel workbook with one row for each column heading of
the sample table (the input term). Each row gives the proposed FAIRe term, its score, the mapper's
call (accept, review or no match) and its reasoning. The reviewer chooses Accept, Reject or Change
from a drop-down, and for Change picks a replacement term from a second drop-down, with the column's
best candidates first. Rows for review are shaded, and the mapper's accepted matches have Accept
filled in already. Reject keeps the column as the lab's own term; a MIxS or Darwin Core term is used
by accepting it. The rows can be sorted or filtered, for example to bring the rows for review to the
top. In Galaxy, the reviewer downloads the sheet, fills it in and uploads it again for apply mapping.
The Shiny app in `shiny/` shows the same sheet on screen.

Here, someone who knows the data made the decisions, recorded with their reasons in
`dev/faire_mapper_seames/reviewer_decisions_18S.tsv`. Two matches for review were accepted, five
rejected, and two of the mapper's accepted matches rejected:

| Input term | Decision | Reason |
|---|---|---|
| Depth (m) | Accept | The depth each sample was taken from (Nominal depth gives the planned depths, which are the same). |
| Volume filtered | Accept | The volume of water collected and filtered for each sample. |
| Sample | Reject | The fastq name of each sample (S001_S13_L001), not the sample material. |
| Sterivex Number | Reject | The number of the filter cartridge, not a read count. |
| Sample ID | Reject | A field label for each sample (SM1_CTD001_Bottom_a), not a material sample ID. |
| Filtration Date | Reject | The date of filtering, not the date the record changed. |
| Nominal depth | Reject | The planned sampling depth, not the depth of the water column. |
| Location | Reject | Station codes, such as S2.1 (Flinders MP). Locality gives geo_loc_name on its own. |
| Filtered by | Reject | Who filtered the water. FAIRe's recordedBy names the people responsible for the dataset. |

Apply mapping takes recordedBy from the person named in project_contact (Bruce Deagle), and writes
project_contact as their email. The four MIxS suggestions were left with no decision, so Phosphate,
Silicate, Pressure and Ammonia stay as the lab's own terms; accepting them would name the columns
after the MIxS terms.

## Step 4. Apply mapping

*Galaxy tool: FAIRe mapper: apply mapping*

The filled-in review sheet, a short list of project-wide values (`project_values_18S.tsv`), ENA's
run report and the ASV table go in. A FAIRe workbook in FAIRe-ator's layout comes out, with a log of
every change: 208 samples, 33 project and 32 sample terms filled, 25 lab columns kept as
user-defined fields, and 16,901 sequences in otuFinal and taxaFinal. The log starts by asking the user to check the workbook
before submitting it anywhere.

- **Values converted:** '30/06/2023' became 2023-06-30, with the date as written kept in
  verbatimEventDate. The times in *Collection Time (UTC)* were joined to the dates and converted to
  local time (+10:00, given on the form): S001's became 2023-06-30T18:06+10:00. '2 L' became 2 and
  L, and 'Flinders Island' became 'Australia: Flinders Island'.
- **Project values** from the methods: target gene 18S V4, the primers TAReuk454FWD1 and the
  modified TAReuk-Rev3 with their sequences, sequencing at the Ramaciotti Centre on a NextSeq 1000,
  SILVA v138.1 and PR2 v5.0.0, the ENVO terms for seawater, and links to the Australian Microbiome's
  protocols for DNA extraction, PCR and the bioinformatics.
- **Libraries:** ENA's run report gave a library for each sample, with both fastq names and
  checksums. Six of the samples are controls sequenced with the samples: a no-template control (a
  PCR negative), a mock community (ATCC1010) and a soil sample on each of the two runs. They have
  reads at the archive but are not in the ASV table, so `make_2L_table.py` adds a row for each from
  the run report, with its sample type and control type. Nine 2 L samples with libraries but no
  details in the record are left out and listed.
- **Read counts:** every sample in the ASV table has 26,739 reads, so the table is rarefied.
  output_read_count is left empty, as FAIRe asks for the reads that passed filtering, before
  rarefying; the log says so. output_otu_num and otu_num_tax_assigned are counted from the table.
  The six controls have no column in it, so their counts are empty, and the log lists them.
- **Taxonomy:** PR2 lineages, with 1,057 sequences named to species and 1,894 to genus. PR2's levels
  are not Linnaean ranks, so names above genus go in scientificName with their PR2 level, and
  *edna2obis: match taxa* can fill kingdom to family from WoRMS. The SILVA lineages are kept in
  identificationRemarks.

## Step 5. Check the workbook

*Galaxy tool: FAIRe-fier*

FAIRe-fier, CSIRO's FAIRe validator, checks every value against the checklist.

- **projectMetadata passes**, with no warnings.
- **sampleMetadata passes.** Its 228 warnings point out the 25 lab columns kept as user-defined
  fields, such as Phosphate and Pressure, which the checklist doesn't list, and suggest giving
  coordinates to at least five decimal places (203 values).

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

The trial's workbook gave the dates only. Since 13 November the workbook also gives each sample's
time of collection, in local time, so FAIRe2ENA now writes S001's collection date as
2023-06-30T18:06+10, in the form ENA's date pattern takes. Dates with times have not yet been sent
to ENA's test service.

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
- **Dates with times.** The trial's dates had no time (step 6).
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
