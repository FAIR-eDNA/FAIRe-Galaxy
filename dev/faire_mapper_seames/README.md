# FAIRe tools on the CSIRO SEA-MES eDNA data

A trial of the FAIRe tools on a published Australian eDNA dataset that has sample tables, ASV tables
with sequences, a methods text and raw reads at NCBI. The first run, on 4 November 2026 with mapper
0.4.0, made no changes for this dataset, so its results are independent. The
problems it found were then fixed (mapper 0.5.0 and the FAIRe2NCBI wrapper), ENA's run report was
added as a library table, and the trial was run again end to end, through the run tables of both
submission tools. The 18S data then went through the same steps, with a sample table made from the
sample details stored below the 18S counts. The 18S run showed two gaps, which were then filled:
apply mapping now reads PR2 and SILVA lineages, and find primers reads primer sequences written in
the methods (with the 18S V4 TAReuk pairs added to the primer table). For 16S, the authors' curated
fish taxa (file 5) then became the final tables, with the ASV table as the raw ones. The COI
table (file 6) then joined the 16S workbook as a second assay, as the same samples and libraries carry
both amplicons. Wilderlab's 12-assay table (file 8) then got its own workbook, from one sample table
for the three sample sets it covers. On 6 November the authors answered our questions (B. Deagle,
below): they did not use the COI data, so COI is now left out; they sent their ASV-level table of
curated 16S names, which now gives the final 16S tables; and they named Wilderlab's repeated
columns, the control types and the 18S instrument. `run.sh OUTDIR` repeats the second run, the 18S
run and the Wilderlab run (set `RSCRIPT` for FAIRe2MDT), in about 14 minutes. A demonstration set cut
from the files is in `demo/seames` (made by `make_demo.py`); `DATA=demo/seames run.sh OUTDIR`
runs every step on it in under a minute.

## Data

Deagle BE, Jayasinghe SA, Bessey C, Bodrossy L, West KM (2025). Environmental DNA data from the RV
Investigator South-East Australian Marine Ecosystem Survey (SEA-MES) voyages (IN2023_V05 and
IN2024_V03), version 2. CSIRO Data Access Portal, [doi:10.25919/ngqx-3557](https://doi.org/10.25919/ngqx-3557).
CC BY 4.0. Raw reads: NCBI BioProject [PRJNA1263580](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1263580/).

| File in `data/` | What it holds |
|---|---|
| `1_SEA-MES_M_samples_metadata_10L.xlsx` | 288 10 L samples (M001 ...), as the NCBI BioSample sheet submitted (MIxS water package; 11 comment lines above the header) |
| `2_SEA-MES_CN_samples_metadata_OCD.xlsx` | 96 deep-tow camera samples (CN...), BioSample sheet with 106 columns, most empty |
| `3_SRA_metadata_SEAMES_18S.xlsx` | the SRA submission sheet for 217 18S libraries: library ID and both fastq file names |
| `4_SEA-MES_16S_ASV_level_output_with_seq.csv` | 16S fish ASV table: 2,967 ASVs with sequences, BLAST taxonomy and counts for 358 samples |
| `5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv` | 235 curated fish taxa: the reads of the ASVs given the same name summed, each row named after one of its ASVs; no sequences |
| `private/SEA_MES_Fish16S_ASV_Feb_27_2025_editColRename.csv` | the authors' ASV-level table of curated 16S names, sent by B. Deagle on 6 November 2026 and not yet published: 2,675 fish ASVs with rank columns, *New_Name* (blank for 62) and *Common_Name*, no sequences, and sample columns named S_M001 and so on. Kept out of the repository (`.gitignore`) until the tool is launched |
| `6_SEA-MES_COI_ASV_level_output_with_seq.csv.gz` | COI Leray ASV table (gzipped): 11,643 ASVs with sequences, BLAST columns and taxonomy (domain to species), and counts for 378 samples (283 10 L, 92 deep-tow and 3 PCR controls); not curated. Not used: the authors did not use it, as its coverage was low and it holds few target metazoan sequences |
| `8_WL_Full_SEA_MES_samples.csv.gz` | Wilderlab's full table for its 12-assay panel (gzipped): 59,623 sequences of up to 150 bp, the assay in a `target` column, NCBI names, ranks and taxon IDs, for 150 samples (CN065 and CN066 each appear twice; the second of each is CN165 and CN166) |
| `7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz` | 18S ASV table (gzipped): 16,901 ASVs, 202 libraries, PR2 and SILVA lineages, and 37 rows of sample details below the counts |
| `filereport_read_run_PRJNA1263580.tsv` | ENA's run report for the BioProject (598 runs): library name, run, sample and study accessions, instrument, fastq files and MD5 checksums |
| `ReadMe_Description.md` | the data record's ReadMe (files, sequencing runs, assays and primers) |
| `methods.txt` | sections 3.2.1-3.2.3 and 4.2.1-4.2.3 of the NESP final report (Deagle et al. 2025, CC BY 4.0) |
| `methods_consolidated.txt` | the methods of sections 3 to 6 of the same report, consolidated (lightly standardised, with settings, instruments and primer sequences kept), as plain text from the Word file; used for 18S |


## What a person did (second run)

- `prepare_table.py` adds the column the guide asks for and the log of apply mapping asks for: the
  type of each control (*Negative control type*, field negative for the 19 controls, which the
  report describes as field filtration controls). The table is otherwise as published.
- `reviewer_decisions.tsv`: confirms Control_Neg as samp_category, and rejects the other 4
  suggestions for review (sample_title as the sampling device, replicate as biological_rep,
  bioproject_accession as associatedSequences, Location as storage location). `review.py` applies it.
- `project_values.tsv`: values for the whole project, from the ReadMe and the report, including the
  16S taxonomy methods from methods.txt: BLASTn against GenBank (85% identity, 96% query coverage),
  the eDNAFlow LCA script, the curation steps, and descriptions of the raw and final tables. Its
  `assay` column marks the values that differ between the assays (target taxa, gene, primers,
  annealing temperature, PCR protocol, amplicon size, taxonomy methods and table descriptions) as
  Fish16S. The COI values (from Table 3-1 of the report) were taken out on 6 November, with COI. The
  instrument, Illumina NextSeq 2000, is from NCBI's SRA run table, which the authors sent; FAIRe asks
  for an OBI term, and OBI has none for the NextSeq 2000 that we could find.
- `accessions.py`: the samples are registered at NCBI already, so the runs are linked to them as a
  lab would after registering. It makes NCBI's BioSample accession table and a stand-in for an ENA
  sample receipt from the run report.

For 18S:

- `make_2L_table.py` turns the 37 rows of sample details below the 18S counts into a sample table:
  one row for each of the 202 samples in the 18S table (190 2 L samples, S001 ..., and the 12 10 L
  samples sequenced for 18S), with the lab's own column names. It adds 7 columns for the details
  that differ between the 2 L and 10 L samples, from the ReadMe and the consolidated methods:
  *Volume filtered*, *Filter pore size (µm)*, *Filter name*, *Filter material*, *Sample processing*,
  *Extraction protocol* and *Extraction kit*. The 12 10 L samples are taken to have the 10 L
  extraction, as they come from the same extracts as the 16S data.
- `reviewer_decisions_18S.tsv`: the review of its crosswalk (below). `review.py` now also adds a row
  for a column the mapper left unmatched (*Collected by* as recordedBy).
- `project_values_18S.tsv`: the assay, gene and region from the ReadMe; the three ENVO terms from
  the 10 L sheet (the same for every sample there); samp_category *sample* (the 18S table has no
  controls); and from the consolidated methods, the primers (TAReuk454FWD1 and modified
  TAReuk-Rev3), the amplification protocol, the sequencing centre, the sampling device, the cleaning
  method and the bioinformatics (trimming, merging, filtering, zOTUs, SILVA v138.1 and PR2 v5.0.0
  with the Wang classifier at 60%).

For Wilderlab:

- `rename_WL_repeats.py` names the second CN065 and CN066 columns of file 8 CN165 and CN166, as the
  authors confirmed (only the header line changes).
- `make_WL_table.py` puts the 150 samples of file 8 into one sample table in the 10 L sheet's form,
  as their three sheets have different columns: the 99 10 L rows as they are (with MQ1 added: 5 L
  of Milli-Q water filtered on the ship alongside the CTD samples, a field negative, as the authors
  described it); 9 deep-tow rows from file 2 (CN167, a "Clean Dry Lab Control", a field negative
  from the deep-tow sampler); 37 2 L rows from the 18S sample table, with the
  date and UTC time as ISO 8601, latitude and longitude as MIxS lat_lon and the volume in mL; and 5
  2 L samples (S099 to S102 and S128) with only their name and voyage, as the record has no details
  for them.
- `reviewer_decisions_WL.tsv`: confirms the control column, deletes sample_title and Location.
- `project_values_WL.tsv`: from section 5 of the consolidated methods, the 12 assays' genes,
  targets and primers. The primer names and references (as DOIs) of 9 assays are from Wilderlab's
  assay details table of 11 June 2025 (ECOSCAN_assay_details_250611.xlsx, which you supplied); LG,
  RJ and XN are not in it. The annealing temperatures of the same 9 assays are from Wilderlab's
  assay details table of 9 July 2026 ([Wilderlab_assay_details_260709.xlsx](https://s3.ap-southeast-2.amazonaws.com/wilderlab.resources/methods/Wilderlab_assay_details_260709.xlsx)): 58 °C for WV and RV,
  55 °C for HD, 52 °C for BE, BU, BX, GD and UM, and 45 °C for CI. Each assay has its own pcr_cond in
  FAIRe's format, and LG, RJ and XN a sentence saying the temperature is not given. The PCR (38 cycles, duplicates, 1.5 µL template, 0.5 µL of each 10 µM primer,
  MyTaq), the library and sequencing steps (NextSeq 1000, P1 XLEAP-SBS cartridge, 15% PhiX, 200
  cycles in one direction), demultiplexing (insect v1.4.0) and DADA2, and the taxonomy (exact
  matches to GenBank and BOLD with lowest common ancestor, SINTAX for the rest, genus or higher for
  BU, BE, BX and UM; not curated). From Wilderlab's laboratory methods (version 2.3.0, 10 July 2026,
  [doi:10.5281/zenodo.21288920](https://doi.org/10.5281/zenodo.21288920)), which the authors sent: the minimum of 5 reads and the removal of human sequences, both of which
  file 8 shows (no count is below 5, and there are no human sequences). Those methods describe
  Wilderlab's current panels, which differ from the report in places (a MiSeq i100 Plus for the
  marine panel, MagMAX beads, 250 cycles, insect v1.4.4); the report's values are the ones for this
  run (confirmed 6 November). Its rule that diet and pet genera need 500 reads was not applied to file 8 (cattle and dog
  sequences have fewer), so it is not given. Those methods give the per-assay annealing temperatures
  in a separate "Wilderlab assay details table", which is the July 2026 table above.

## Results (second run, mapper 0.5.0)

**Propose mapping.** The 10 L table as published, with no setting changed: the 11 comment lines
are skipped, and 12 columns accepted, all correct. MIxS lat_lon fills decimalLatitude and
decimalLongitude, and *depth fills minimumDepthInMeters and maximumDepthInMeters. Control_Neg (Y or
N) is proposed for review as samp_category, with yes as *negative control*. With the control type
added: 13 accepted, all correct. The deep-tow table: 48 accepted, among them its lat_lon, which
also carries a minus sign ("-42.055938 S"). 40 of the 48 are empty columns whose MIxS names are
FAIRe terms (correct, but they write nothing).

**Find primers.** The 16S fish pair (Fish16S, Berry et al. 2017) and the COI Leray pair
(mlCOIintF/jgHCO2198), with 6 other candidates for review. The two right pairs now come first, as
the methods give their sequences; the 6 others match a primer name only.

**Apply mapping.** 288 samples and 52 FAIRe terms. The library table gave one experimentRunMetadata
row for each of the 288 samples: 381 libraries have *16SFish* in their name, 288 match a sample by
the start of their name (M159_16SFish_LerayCOI), and 93 of other samples (deep-tow and one PCR
control) are left out and listed. Each row has lib_id, both file names, their MD5 checksums, the
run ID of the 16S ASV table, and links to the run, the BioSample and the BioProject. platform,
lib_layout and checksum_method went to projectMetadata, and neg_cont_0_1 to 1.

**16S taxonomy, raw and final.** The ASV table (file 4) holds the authors' preliminary taxonomy, from
BLASTn and the eDNAFlow LCA script, with bacteria, viruses and copepods among the fish. The curated
table (file 5) holds 235 fish taxa. The authors curated each ASV, then summed the reads of the ASVs
given the same name, and each row carries the ID of one of its ASVs. The *Sardinops sagax* row, for
example, holds the reads of the 234 ASVs that file 4 assigns to Sardinops, all but 5 of 7.05
million. So file 4 went in as otuRaw and taxaRaw (2,967 sequences, 276 samples) and file 5 as otuFinal
and taxaFinal (235 taxa, 276 samples). An earlier run had file 4 as the final table, so the MDT
workbook would have given GBIF the uncurated names.

- dna_sequence: file 5 has none. FAIRe's final OTU tables name each taxon's row after its most
  abundant ASV and sum the reads of all its ASVs (the answer to the FAIRe question, 5 November), and
  file 5 does this wherever the preliminary taxonomy lets us check (*Trachurus*, *Sardinops*,
  *Scomber* and others). So every row now takes the sequence of the ASV it is named after, from file
  4. 83 rows hold that one ASV (the same reads across all 358 count columns); the other 152 hold
  several, which identificationRemarks says. FAIRe's taxaFinal lists every ASV, one per row; that
  needs each ASV's curated name, which the record does not have, so taxaFinal holds the 235 ASVs the
  rows are named after, and the log says the others are missing.
- Names: *New_Name* gives the name and its rank: 141 to species, 64 to genus, 26 to family and 4 to
  order. 93 names such as *Trachurus Sp* or *Diaphus Sp1* are written as the genus (or family or
  order), with the name as given in verbatimIdentification. Three names have a genus that differs
  from the genus column: *Spiniraja whitleyi* (Dipturus) and *Chrysophrys auratus* (Pagrus) are
  current names, and *Emmelicthys nitidus* is a misspelling of *Emmelichthys nitidus*. The name's
  genus is written, and the log lists all three. *Common_Name* and *Sp_Level* have no FAIRe term.
- projectMetadata now has the taxonomy methods (otu_db, tax_assign_cat, otu_seq_comp_appr, the
  cut-offs, the LCA rule, the geographic check, the curation steps, and descriptions of the raw and
  final tables).

**FAIRe-fier.** sampleMetadata passes, with 32 warnings: 9 user-defined fields, and coordinates with
fewer than 5 decimal places in the published table. projectMetadata has 2 errors: `checkls_ver` (the
known FAIRe-ator format) and recordedBy, which is not in the files.

**Conversions.** FAIRe2MDT: 288 samples, 37 study terms, an OTU table of the 235 curated taxa and
276 samples, and a Taxonomy sheet with their names.
FAIRe2QIIME: a metadata file and, now that the file names are known, a manifest, each for the 288
libraries. FAIRe2ENA samples: 288 samples.

**Submission tables, against what the authors submitted.**

- FAIRe2NCBI BioSample, with MIxS units on (the default): 288 samples. Of the 20 fields in both
  sheets, 15 are identical, including collection_date and lat_lon; the other 5 hold the same values
  with the MIxS unit added (*depth, salinity, samp_vol_we_dna_ext, size_frac_low, temp), and *depth
  is "not applicable" for the 19 controls, which the authors left empty.
- FAIRe2NCBI SRA: 288 rows. library_ID, the BioSample, both file names and the instrument match
  ENA's report for all 288.
- FAIRe2ENA experiments and runs: 288 experiments and 288 runs, with MD5 checksums for both files.

## Results with the authors' answers (6 November 2026)

Bruce Deagle answered our questions on 6 November: the 18S libraries were sequenced on a NextSeq 1000,
as ENA says (NCBI's SRA run table, which he sent, gives NextSeq 2000 for the 381 16S libraries and
NextSeq 1000 for the 217 18S ones; the ReadMe's MiSeq is wrong); the second CN065 and CN066 columns
of Wilderlab's table are CN165 and CN166; MQ1 was a field filtration control (5 L of Milli-Q water
filtered on the ship alongside the CTD samples) and CN167 a field negative from the deep-tow
sampler; the COI amplicons were added at the last minute, gave low coverage and few target
metazoan sequences, and were not used; and he sent the authors' ASV-level table of curated 16S
names. Wilderlab's laboratory methods came too (below). We changed the trial to match.

**16S final tables from the ASV-level curated names.** The table has 2,675 fish ASVs, with the
counts of file 4 for each, rank columns, *New_Name* and *Common_Name*, and no sequences. Its sample
columns are named S_M001 and so on; apply mapping now reads names that all carry one prefix
without it (276 columns). It went in as the final table of Fish16S, with file 4 as raw, so it gives
only otuFinal and taxaFinal, with each ASV's sequence from file 4 (new in apply mapping).

- taxaFinal lists the 2,613 ASVs with a curated name, each with its own sequence, as FAIRe asks; the
  62 with none (removed in curation) are in the raw tables only. otuFinal has the 235 taxa, with
  each taxon's reads summed under its most abundant ASV, and the same reads as file 5 (40,916,731
  in the 276 samples). 11 of the 235 rows take another ASV's ID than file 5, as the most abundant
  ASV is chosen over the workbook's samples; file 5 counts the deep-tow columns too, and three of
  its rows are named after a less abundant ASV.
- identificationRemarks on each ASV of the 152 taxa with several ASVs says under which ASV its
  reads are summed.
- Names: four names have a genus that differs from the genus column (188 ASVs): *Chrysophrys
  auratus* (Pagrus) and *Spiniraja whitleyi* (Dipturus), which are current names; *Allomycterus
  pilatus* (one ASV with Diodon, a reassignment in curation); and *Emmelicthys nitidus* (178 ASVs),
  the misspelling. One ASV (ASV_431) has *Atlantic Salmon* as its curated name and *Salmo salar*
  as its common name, swapped, as in file 5. Apply mapping had written *Atlantic* as its name; it
  now reads two capitalised words whose first is in no rank column as not a scientific name, warns,
  keeps the name in verbatimIdentification and names the row from the rank columns (*Salmo*, genus).
- FAIRe2MDT wrote all 2,613 ASVs into the Taxonomy sheet, against 235 rows of the OTU table. The
  wrapper now leaves out the taxonomy rows that have no OTU table row, with a note, as MDT wants
  one taxonomy row for each OTU row.
- experimentRunMetadata has 288 rows, one for each library (M159_16SFish_LerayCOI_Fish16S_AGRF_2024-12);
  instrument (Illumina NextSeq 2000) is in projectMetadata, so the log no longer asks for it.
- FAIRe-fier, FAIRe2NCBI and FAIRe2ENA give the same results as before: sampleMetadata passes,
  projectMetadata has the known two errors, and the BioSample and SRA tables match what the
  authors submitted for all 288 samples.

The demonstration set (`demo/seames`) now leaves out COI, has the N18 deep-tow pair (CN165 and
CN166, 25 samples in all), and, when the private table is there, a cut of it in `demo/seames/private`
(kept out of the repository). Without the private table, `run.sh` takes the final tables from file 5,
as before.

## Results for COI, the second assay (5 November 2026)

COI is left out of the trial since 6 November, as the authors did not use it. These results show
how the tools handle two assays in one library, which the tests also cover.

**Apply mapping.** One workbook for both assays: assay_name is "Fish16S | COILeray" for every sample,
and projectMetadata has a column for each assay. The COI table went in as otuFinal_COILeray and
taxaFinal_COILeray (11,643 ASVs, 285 samples), and the 16S sheets are now named by assay
(otuRaw_Fish16S and so on). The 92 deep-tow columns and P007, which is not in the sample table, are
left out; M098, M101 and P004 have no COI column. Each library holds both amplicons
(M159_16SFish_LerayCOI), so experimentRunMetadata has 576 rows, one for each library and assay, with
the same files. As FAIRe takes a library to be one amplicon of a sample, each row has its own lib_id:
the library name, assay and run (M159_16SFish_LerayCOI_Fish16S_AGRF_2024-12 and
M159_16SFish_LerayCOI_COILeray_AGRF_2024-12).

**Taxonomy.** As published, with no curation, so the table keeps every BLAST hit. By reads, 12% are
metazoan (862 of the 1,253 metazoan ASVs are arthropods), 4% human, 48% other eukaryotes such as
green algae and pelagophytes, and 36% bacteria. 9,630 ASVs are named to genus and 891 to species.
Bacteria, Archaea and Viruses go to kingdom; Eukaryota is left out of kingdom, as for 16S. The table
went in as final because it is the only one for COI, as for 18S, and the guide writes a single table
as final; otu_final_description says that it is not curated.

**FAIRe-fier.** The same two errors as with 16S alone (`checkls_ver` and recordedBy). It checks the
assay columns too: a word put into COI's annealingTemp was reported, though under the record *ALL*,
with no assay named. It accepts the inosines (I) in the reverse primer.

**Conversions.**

- FAIRe2MDT, once for each assay. Fish16S gives the same Samples, Taxonomy and OTU sheets as before,
  and the Study sheet now also has annealingTemp (54). COILeray: 26 study terms, 11,643 sequences
  and 285 samples, with no taxonomy methods, as the report describes the bioinformatics for 16S only.
- FAIRe2QIIME: a metadata file and a manifest for each gene, 288 libraries each. Both manifests list
  the same files, which suits QIIME, where each assay is cut from the reads by its primers.
- FAIRe2NCBI BioSample and FAIRe2ENA samples: 288 samples as before.
- FAIRe2NCBI SRA and FAIRe2ENA runs: each library holds both amplicons, so the 576 rows give one SRA
  row, and one ENA experiment and run, for each of the 288 libraries, as the authors submitted. The
  SRA title and design description name both assays ("M159: Fish16S and COILeray metabarcoding of
  ..."; "2 assays in one library. Fish16S: ...; COILeray: ..."). library_ID is the library's own
  name (the lib_id without its assay and run), and it, the BioSample, both files and the instrument
  match ENA's report for all 288. Before the tools joined such rows, both
  stopped on the repeated libraries and files.

## Results for Wilderlab (5 November 2026)

**Propose mapping** on the Wilderlab sample table: 13 accepted, all correct; 3 for review (the
control column, confirmed; sample_title and Location, deleted).

**Apply mapping.** 148 samples and 48 FAIRe terms. Apply mapping now splits a table by a column that
gives each row's assay: the 12 assay names come from the *target* column, and each assay gets its
otuFinal and taxaFinal sheets (CI 17,003 sequences, XN 2,530, RJ 163 and so on). CN065 and CN066
each appear twice with different counts; the first of each is used and the log says so, as the
table does not say which samples the others are. The deep-tow depth "250-350" fills
minimumDepthInMeters and maximumDepthInMeters with 250 and 350 (new), and RJ's sequences of 20 bases
are read as sequences, under the header *sequence*. Apply mapping takes about 1.5 minutes.

**Taxonomy.** Wilderlab gives an NCBI name, rank and taxon ID for each sequence. The name now fills
its rank term (a species its genus and specificEpithet), and taxonID takes the ID. 58% of the
sequences are named *root* (NCBI's taxon 1), meaning no assignment: from 6% for RV to 97% for XN.
These get no scientificName, taxonRank or taxonID, and *root* is kept in verbatimIdentification.
Names such as *unclassified Paracalanus*, NCBI's placeholders, are written as the group named, and
NCBI's *no rank* is left out; *clade* is written as *other: clade*.

**FAIRe-fier.** projectMetadata has the known two errors (`checkls_ver`, recordedBy). sampleMetadata
has 39 errors, all where the record has no details: 7 terms each for S099 to S102 and S128, the
date, place and control type of MQ1, and the control type of CN167.

**Conversions.** FAIRe2MDT makes a workbook for each of the 12 assays (148 samples each, 150 since 6 November). FAIRe2QIIME
writes 7 metadata files and manifests for the 12 assays: upstream names them by gene, so assays of
the same gene overwrite each other (RV and LG by RJ for 12S, WV by HD, BE by BU, CI by XN). The
BioSample and ENA sample tables are not made: the samples are registered already, and both tools
rightly stop on the five 2 L samples that have no details.

**With the authors' answers (6 November).** `rename_WL_repeats.py` names the second CN065 and CN066
columns CN165 and CN166, so the table has 150 samples (99 10 L, 42 2 L and 9 deep-tow) and apply
mapping no longer warns of repeated columns. MQ1 and CN167 are field negatives, so FAIRe-fier
reports 37 errors in sampleMetadata, all where the record has no details: 7 terms each for S099 to
S102 and S128, and the date and place of MQ1. projectMetadata now has the instrument (NextSeq
1000), the reagent cartridge, the primer volumes and concentrations, insect and DADA2, and the
minimum of 5 reads.

## Results for 18S (mapper 0.5.0)

**Propose mapping** on the 18S sample table, which the mapper had not seen: the 37 columns from the
18S table and the 7 added, 44 in all. 21 accepted, 4 for review, 19 not matched.

- 18 of the 21 accepted are correct: the sample name (*Sample No.*), depth (to both depth terms),
  coordinates, *Locality* (geo_loc_name), collection and extraction dates, temperature, salinity,
  oxygen, nitrite, and the 7 added columns (volume, split into samp_size and samp_size_unit; pore
  size; filter name and material; processing; extraction protocol and kit).
- 3 accepted are wrong or a poor choice: *Sample* (the fastq file name of each sample) as the
  sampling device, the known problem of *sample* matching *sampler*; *Location* (station codes such
  as S2.1) combined with *Locality* into geo_loc_name; and *Filtered by* as recordedBy, which took
  the term from *Collected by*.
- None of the 4 suggestions for review is right: *Sterivex Number* as a read count, *Sample ID* as
  materialSampleID, *Filtration Date* as mod_date and *Nominal depth* as tot_depth_water_col.
- Of the 19 not matched, *Collected by* is the only one with a FAIRe term. FAIRe has none for
  phosphate, silicate, ammonia or NOx, pressure, whether a sample was processed, the voyage, CTD
  and rosette details, or the sampling times in separate columns.

The review deleted the 7 wrong rows and added *Collected by* as recordedBy.

Since 5 November 2026 a word and its agent noun no longer match, so *Sample* is not accepted as the
sampling device: it goes to review as env_medium, at a low score, which the review deletes as
before (20 accepted, 5 for review). Every output after the review is unchanged.

**Apply mapping.** 202 samples and 54 FAIRe terms, with 25 user-defined fields. Dates written day
first (30/06/2023) became ISO dates. geo_loc_name is "Australia: Flinders Island" and the like. The
ASV table's 202 columns are file names (S001_S13_L001), all matched to the samples; the sample
details below the counts are left out. ENA's run report, filtered to the 217 libraries with *_18s*
in their name, gave a library row for each of the 202 samples; the other 15 (9 S samples not in the
ASV table, and two each of a mock community, a no-template control and a soil sample) are left out
and listed.

**Taxonomy.** Apply mapping reads the *PR2 tax* lineages as PR2 v5 levels and keeps each *Silva
138.1 tax* lineage in identificationRemarks ("also classified as Silva 138.1 tax: ..."). FAIRe's
taxonomy terms are Linnaean ranks, so only the genus and species go to genus and specificEpithet. A
higher name becomes scientificName with taxonRank *other: PR2 family* and the like, as PR2's levels
above genus are not FAIRe's kingdom to family, and identificationRemarks on every row says PR2 was
used. otu_db names both databases (*SILVA v138.1 | PR2 v5.0.0*). The full
lineage stays in verbatimIdentification, and confidence_score is the classifier's confidence in the
lowest name, on FAIRe's 0 to 1 scale. Of the 16,901 sequences, 1,057 are named to species and 1,894
to genus; 5,097 stop at a PR2 family, 1,833 at an order, 1,813 at a class and 960 higher; 3,695 are
Eukaryota only (PR2 gives *Eukaryota_unclassified* below), and 552 have no name. Setting *Lineage
column to use* to *Silva 138.1 tax* uses SILVA's ranks instead (phylum to genus).

**Find primers** on the consolidated methods: 16 pairs, all written as sequences in the text. The
first is the 18S pair, TAReuk454FWD1 with the modified TAReukREV3 of the Australian Microbiome
protocol, and the second is the original Stoeck et al. (2010) pair, matched on its names. The other
14 are the other assays the report describes, most of them the Wilderlab panel. Three of these are
not in the primer table (two 12S pairs and a COI pair), so they are listed as written, with the gene
from the text.

**FAIRe-fier.** sampleMetadata passes. projectMetadata has one error, `checkls_ver` (the known
FAIRe-ator format). Before the consolidated methods gave the primers, it also had the two primer
sequences.

**Conversions.** FAIRe2MDT: 202 samples, 31 study terms, an OTU table of 16,901 sequences and 202
samples, and a Taxonomy sheet of 9 fields, with names for 16,349 sequences. FAIRe2QIIME: a metadata file and a manifest for the 202 libraries.
FAIRe2NCBI BioSample: 202 samples, with *Sample_ID* telling apart the pairs of samples (_a and
_b) that have the same attributes. FAIRe2ENA: 202 samples, 202 experiments and 202 runs.

**FAIRe2NCBI SRA, against what the authors submitted.** 202 rows. library_ID, the BioSample, both
file names and the instrument match ENA's report for all 202. Against the authors' SRA sheet for 18S
(file 3), all 202 library IDs are there (ENA writes *_18s* where the sheet has *_18S*), and
library_strategy, library_selection, library_layout, platform and filetype are the same for all.
These differ:

- title: FAIRe2NCBI writes its own ("S249: Euk18S metabarcoding of marine metagenome in Australia:
  Gabo"); the authors used the field label (SM2_CTD61_Surface);
- library_source: FAIRe2NCBI writes METAGENOMIC, the authors GENOMIC;
- design_description: FAIRe2NCBI writes a sentence with the gene, region, primers and protocol
  ("Metabarcoding of 18S rRNA (SSU eukaryote) gene V4 region using PCR primers TAReuk454FWD1
  (CCAGCASCYGCGGTAATTCC) and TAReuk-Rev3 (modified) (ACTTTCGTTCTTGATYRATGA) using protocol at
  Australian Microbiome protocol meth_5.1"); the authors wrote "Amplicons demultiplexed broad 18S v4
  assay";
- instrument_model: empty in the authors' sheet; NextSeq 1000 in ours, from ENA's report;
- the file names: ENA's copies in ours (SRR33983199_1.fastq.gz), the names as submitted in the
  authors' sheet (S249_S88_L001_R1_001.fastq.gz).

## Problems found in the first run, and what changed

Mapper and apply mapping (fixed in 0.5.0):

| First run (0.4.0) | Now |
|---|---|
| The 11 comment lines above the header of an NCBI or ENA sheet had to be skipped by setting the header row | Comment lines starting with # are skipped (a # row with several cells, such as `#OTU ID`, is still the header) |
| MIxS lat_lon in one column ("40.57773667 S 148.7301917 E") was not split | Split into decimalLatitude and decimalLongitude, keeping the digits given; a redundant minus sign with S (the deep-tow table's "-42.055938 S") is read as south |
| A yes/no control column was proposed as neg_cont_0_1, a project-level yes or no | Proposed as samp_category (yes *negative control*, no *sample*); apply mapping sets neg_cont_0_1 to 1 and asks for neg_cont_type |
| One depth column filled minimumDepthInMeters only, and FAIRe2NCBI takes *depth from maximumDepthInMeters | One depth fills both, unless a header says which end of a range it holds |
| Dates saved at midnight were written with the time (2023-06-30T00:00:00), which NCBI does not accept | Written as dates (2023-06-30) when every time is midnight |
| The 18S table did not match the samples: its columns are fastq file names (M108_S7_L001) | Illumina file names are matched to sample names; rows of sample details below the counts are left out |
| 40 empty columns of the deep-tow table were accepted | Still matched when the header names a term, as the benchmark counts these, but empty columns not matched are no longer kept as empty user-defined fields |
| Domain values (Eukaryota) went to kingdom; Query_coverage was not used | Eukaryota is not written to kingdom; Query_coverage fills percent_query_cover. BLAST identity ranges (99.107-99.554) are kept as text, which FAIRe allows for percent_match |
| The log's note on trailing zeros appeared for every decimal column, with a fixed example | Only for columns with trailing zeros, with an example from the column |
| No library table: experimentRunMetadata had samp_name, assay_name and seq_run_id only | Library tables (ENA or SRA run reports, the SRA submission sheet, a lab's run sheet) give lib_id, files, checksums and links |

FAIRe2NCBI (upstream, NOAA AOML; worked around in our wrapper, and the upstream scripts unchanged):

| First run | Now |
|---|---|
| With MIxS units on, it stopped on a column of whole numbers (samp_store_temp, all -80) | The wrapper reads the workbook with each cell's own type, so units are added (-80 degree Celsius) |
| lat_lon was rounded to 3 decimal places (40.578 S) | Keeps the decimal places of the workbook (40.57773667 S) |
| Whole numbers gained ".0" (14 became 14.0) | Stay whole |

The 18S run found one more (fixed in 0.5.0): date_ext was not converted, because the checklist gives
it no format. It is now read as a date, as its example is an ISO date.

The benchmark and the four Dryad and two Australian trials give the same scores with 0.5.0 as with
0.4.0.

## Still open

- **For the authors to correct in the data record** (answered 6 November; Bruce Deagle plans to
  update the record): the second CN065 and CN066 headers of file 8 (CN165 and CN166); the
  ReadMe's MiSeq run for 18S (NextSeq 1000); *Emmelicthys nitidus* for *Emmelichthys nitidus* (178
  ASVs, and its row in file 5); and ASV_431, whose curated and common names are swapped (*Atlantic
  Salmon* and *Salmo salar*), in the ASV-level table and in file 5.
- **Still to ask the authors**: the details of S099 to S102 and S128; what CN167 filtered (Bruce
  thinks the water used to rinse the filtration equipment, 1 L); and whether the demonstration set
  can be offered as Galaxy demonstration data, with the curated table once it is published.
- **Wilderlab's annealing temperatures for LG, RJ and XN.** These three assays are not in
  Wilderlab's assay details tables of June 2025 or July 2026. (Wilderlab's earlier methods,
  [version 2.2.4](https://s3.ap-southeast-2.amazonaws.com/wilderlab.resources/methods/Wilderlab_metabarcoding_methods_2.2.4.pdf)
  of November 2024, give 58 °C for LG.)
- **BX annealing temperature.** The July 2026 table gives 52 °C, and Wilderlab's methods version
  2.2.4 (November 2024) give 55 °C. Which applied to these samples is a question for the authors.
- **Wilderlab's PCR settings in the July 2026 table** differ from the report for some assays: the
  extension at 72 °C is 20 or 25 s (the report gives 15 s for all), BU and UM have 34 cycles (38),
  and WV, RV and CI are run in quadruplicate (duplicate). The values follow the report, as the
  table is a year later than this run.
- **Wilderlab's GD code.** The report's GD primers (SCLER5.8SForw and SCLER28SRev) are the GC pair
  in Wilderlab's June 2025 table, where GD has an Acropora reverse primer (Acro874_Rev). File 8's GD
  reads (hydrozoans, siphonophores and sponges, no Acropora) fit the report's pair, so the code may
  have changed after this run. The values follow the report.
- **Primer table.** All 20 pairs in Wilderlab's June 2025 table are in the bundled primer table with
  the same sequences, mostly under Wilderlab's codes (WVF, HDF). The table gives the published names
  (12S-V5-F, MiDeca-F) and DOIs, which the primer table could take too. It attributes CI's forward
  primer to Leray et al. 2013 (modified mlCOIintF), where the primer table names it fwhF2.
- **FAIRe2QIIME (upstream)** names its outputs by gene, so with several assays of one gene only the
  last is kept.

- **Not in the consolidated methods**: the 18S PCR conditions
  (cycles, annealing, volumes; they are in Australian Microbiome protocol meth_5.1), the membrane of
  the Sterivex GP filters (filter_material), and the units of oxygen and nitrite. The references for
  the 18S primers are not given either; the primer table now has them (Stoeck et al. 2010, and the
  Australian Microbiome protocol for the modified reverse primer).
- **ENA's file names are ENA's copies** (SRR33695780_1.fastq.gz), with their own checksums. A
  report with submitted_ftp and submitted_md5 would give the files as the lab submitted them; the
  18S SRA sheet has the submitted names (S001_S13_L001_R1_001.fastq.gz).
- **Two BioSamples for 12 samples.** The 12 10 L samples sequenced for 18S were registered again
  with the 18S libraries, so each has a second BioSample. `accessions.py` takes those of file 1 for
  16S and those registered with the 18S libraries for 18S.
- **Instrument** (settled 6 November). The run report names NextSeq 2000 for 16S and NextSeq 1000
  for 18S, and the authors confirmed both; the ReadMe's MiSeq v2 2x250 run for 18S is wrong. The
  values for the whole project now give them: Illumina NextSeq 1000 [OBI_0003606] for 18S and
  Wilderlab, and Illumina NextSeq 2000 for 16S, which has no OBI term that we could find.
- **Upstream FAIRe2NCBI SRA** writes "NA" into the design description for each empty field
  (primers, region, protocol), and METAGENOMIC as library_source. Its "using protocol at" expects a
  link, and the methods give a protocol name.
- **Mapper:** a column of station codes next to a locality column joins geo_loc_name. (*Sample* no
  longer matches *sampler*, since 5 November.)
- **Sample names differ between files**: the deep-tow table has CN001 to CN003 where the ASV table
  has CN01 to CN03.
- **FAIRe2ENA's log** (upstream) says "Generated ENA XML with 25961 samples" for 288: it counts the
  lines of XML. The XML holds 288 samples, and the wrapper's own line says so.
- Not run: edna2obis (needs WoRMS and GBIF, or a reviewed mapping table).
