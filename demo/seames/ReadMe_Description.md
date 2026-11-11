### Overview of data provided

Details of the project (NESP Marine and Coastal Project 4.23) and the
final report are available on the NESP Marine and Coastal Hub website:
<https://www.nespmarinecoastal.edu.au/project/4-23/>. The final report
has also been attached to this data record.

The information provided here includes data about the samples (files
1-3) as well as eDNA data collected from the samples (Files 4-8: OTU
tables with sequence counts) derived from eDNA metabarcoding (Table 1).
Information on the various sequencing runs is provided below. The
metabarcoding assays are outlined in Table 2 and 3.

**Sequence data (fastq files)** are available on NCBI under **BioProject
PRJNA1263580**: <https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1263580/>

**Table1**: SEA-MES eDNA datasets

<table>
<colgroup>
<col style="width: 46%" />
<col style="width: 53%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>File Name</strong></th>
<th><strong>Description</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>1 SEA-MES_M_samples_metadata_10L.xlsx</td>
<td><p>Sample information for 10L eDNA samples processed with 16S mtDNA
fish and COI Leray markers. The sample names all start with letter “M”
and match column names in the ASV tables. PCR control samples start with
the letter “P”.</p>
<p>This table matches the data submitted to the NCBI BioSample database
and is linked to the sequence files (fastq) deposited in
GenBank</p></td>
</tr>
<tr class="even">
<td>2 SEA-MES_CN_samples_metadata_OCD.xlsx</td>
<td><p>Information on samples collected as part of an evaluation of a
CSIRO eDNA sampler deployed on the deep tow camera system. The eDNA
samples were processed with 16S mtDNA fish and COI Leray markers. The
sample names all start with letter “CN” and match column names in the
ASV tables. PCR control samples start with the letter “P”.</p>
<p>This table matches the data submitted to the NCBI BioSample database
and is linked to the sequence files (fastq) deposited in
GenBank.</p></td>
</tr>
<tr class="odd">
<td>3 SRA_metadata_SEAMES_18S.xlsx</td>
<td><p>Sample information for 2L and 10L eDNA samples processed with the
18S v4 broad eukaryote marker. The sample names start with letter “S”
(for 2L samples, collected on 0.22 um filters) and “M” (for 10L samples,
collected on 0.45 um filters) and match column names in the ASV
tables.</p>
<p>This table matches the data submitted to the NCBI BioSample database
and is linked to the sequence files (fastq) deposited in
GenBank</p></td>
</tr>
<tr class="even">
<td>4 SEA-MES_16S_ASV_level_output_with_seq.csv</td>
<td><strong>16S mtDNA fish</strong> Amplicon Sequence Variant (ASV)
table with counts of sequences recovered after bioinformatic processing.
The ASV sequences are provided in the table along with preliminary
taxonomic assignment based on a BLAST search (see NESP report for
details on bioinformatics). Curation of data is required to check
taxonomic assignments. This information is derived from SEA-MES eDNA
sequence data set 1 (see below).</td>
</tr>
<tr class="odd">
<td>5 SEA_MES_Fish16S_Tax_Feb_27_2025.csv</td>
<td><strong>16S mtDNA fish</strong> table with sequence counts for 235
fish taxa from SEA-MES eDNA sequence data set 1. The fish taxonomic
assignments were curated at the ASV level and counts merged for ASV
sequences assigned to the same taxa. The taxonomic assignments are
expected to improve when new reference sequences are released from
National Biodiversity DNA Library (<a
href="https://research.csiro.au/dnalibrary/">https://research.csiro.au/dnalibrary/</a>).</td>
</tr>
<tr class="even">
<td>6 SEA-MES_COI_ASV_level_output_with_seq.csv</td>
<td><strong>COI Leray</strong> ASV table with counts of sequences
recovered after bioinformatic processing. The ASV sequences are provided
in the table along with preliminary taxonomic assignment based on a
BLAST search (see NESP report for details on bioinformatics). Curation
of data is required to check taxonomic assignments. This information is
derived from SEA-MES eDNA sequence data set 1 (see below).</td>
</tr>
<tr class="odd">
<td>7 SEA-MES_2025_EUK_18S_for_DAT.csv</td>
<td><strong>18S v4</strong> (broad eukaryote marker) ASV table with
counts of sequences recovered after bioinformatic processing. ASV table
rarefied to 26,739 reads. The ASV sequences are provided in the table
along with taxonomic assignments based on both the Silva (v138.1) and
PR2 databases. This information is derived from SEA-MES eDNA sequence
data set 2 (see below).</td>
</tr>
<tr class="even">
<td>8 SEA-MES Wilderlab data</td>
<td><p><strong>Tree of Life metabarcoding</strong> ASV table</p>
<p>A subset of 150 eDNA samples were sent to a commercial laboratory
(Wilderlab: <a href="https://wilderlab.co/">https://wilderlab.co/</a>)
where sequence data from 12 different assays were generated (targets
include bacteria, crustaceans, fish, etc; information on the assays is
provided below). The ASV table provides the sequence recovered, assay
used, provisional taxonomy and sequence counts for each sample.</p>
<p>The sample metadata for each of the samples (includes “M”, “CN and
“S” samples) are provided in the metadata (first three files listed in
this table).</p></td>
</tr>
</tbody>
</table>

### 

### DNA sequence data produced during the project

1)  **SEA-MES eDNA sequence data set 1**: Australian Genome Research
    Facility (AGRF) Illumina sequencing, December 2024

<u>Sequencing</u>: NextSeq 2000, P1 flow cell, 300 cycles PE; 102
million sequences; 61.09 gigabases (Gb) data

<u>Amplicons</u>: 16S mtDNA fish and COI Leray

<u>Samples</u>: 10 L samples from both voyages (n= 288; Section 3 of
report); deep towed camera related samples from voyage 2 (n= 96; Section
4 of report)

2)  **SEA-MES eDNA sequence data set 2:** Ramaciotti Centre for Genomics
    Illumina sequencing, February 2025

<u>Sequencing</u>: MySeq v2 2x250 bp run; 16 million sequences, 12.64
gigabases of data.

<u>Amplicons</u>: 18S v4

> <u>Samples</u>: 2L samples from both voyages (n=199; Section 5 of
> report); plus select 10L samples (n=12; Section 3 of report)

3)  **SEA-MES eDNA sequence data set 3**: Wilderlab Illumina sequencing,
    December 2024

<u>Sequencing</u>: NextSeq; 76.9 million sequences

<u>Amplicons</u>: 12 amplicons (see Section 6 of the report).

<u>Samples</u>: 10 L (n=90) and 2 L (n=42) samples from voyage 1; deep
towed camera comparison samples (n=16) from voyage 2 (Section 6 of the
report)

<u>Additional DNA sequencing from the SEA-MES samples outside of the
NESP project</u>

4)  **SEA-MES eDNA pilot data set**: AGRF Illumina sequencing, December
    2023

<u>Sequencing</u>: MiSeq, 300 cycle; 11 million sequences; 3.29 Gb of
data

<u>Amplicons</u>: 16S mtDNA fish

> <u>Samples</u>: 10L, 2L and deep towed camera test samples from voyage
> 1 (n=285 total; the 10L and 2L samples were re-run in SEA-MES eDNA
> data set 1 and 2).

5)  **SEA-MES fish mtDNA reference sequences**: Ramaciotti Centre for
    Genomics Sanger sequencing of DNA from voucher specimens (Australian
    National Fish Collection, CSIRO)

<u>Sequencing</u>: Sanger dideoxy; 550 to 600 bp

<u>Amplicons</u>: 16S mtDNA fish – longer fragment

<u>Samples</u>: Fish specimens (n=199). Sequences have been made
available GenBank
([h](https://www.ncbi.nlm.nih.gov/genbank/)ttps://www.ncbi.nlm.nih.gov/genbank/)
15-APR-2024.

**Table 2:** PCR assay information for eDNA metabarcoding of the 10L and
deep-towed camera samples

| *PCR assay* | *Target taxa* | *Primer name*    | *Sequence (5′-3′)*         | *Target length* | *Annealing (°C)* | *Reference*            |
|-------------|---------------|------------------|----------------------------|-----------------|------------------|------------------------|
| *16S Fish*  | Fish          | 16SF/D           | GACCCTATGGAGCTTTAGAC       | ~180–230 bp     | 54               | Berry *et al.* (2017)  |
|             |               | 16S2R-degenerate | CGCTGTTATCCCTADRGTAACT     |                 |                  | Deagle *et al.* (2007) |
| *COI Leray* | Metazoa       | mlCOIintF        | GGWACWGGWTGAACWGTWTAYCCYCC | 313 bp          | 46               | Leray *et al.* (2013)  |
|             |               | jgHCO2198        | TAIACYTCIGGRTGICCRAARAAYCA |                 |                  |                        |

**Table 3:** The 12 assays used by Wilderlab for metabarcoding eDNA
samples. Locus-specific sections of fusion-tag primers used are shown.
Asterisks signify long-amplicon assays that are run with a single index,
reading through only the first 150 bp of the amplicon. References for
primer pairs are provided; an M indicates the primer has been modified
from original.

<table>
<colgroup>
<col style="width: 9%" />
<col style="width: 9%" />
<col style="width: 41%" />
<col style="width: 14%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr class="header">
<th>Assay code</th>
<th>Gene region</th>
<th>Primer sequences</th>
<th>Target</th>
<th>Reference</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>WV</td>
<td>mt16S</td>
<td><p>GACGAGAAGACCCTWTGGAGC</p>
<p>CCRYGGTCGCCCCAAC</p></td>
<td>Vertebrates</td>
<td>(Nester <em>et al</em>. 2020)</td>
</tr>
<tr class="even">
<td>RV</td>
<td>mt12S</td>
<td><p>TTAGATACCCCACTATGC</p>
<p>TAGAACAGGCTCCTCTAG</p></td>
<td>Vertebrates</td>
<td>(Riaz <em>et al</em>. 2011)</td>
</tr>
<tr class="odd">
<td>LG</td>
<td>mt12S</td>
<td><p>CGGCGTAAAGWGTGGTTAGG</p>
<p>CATAGTGGGGTATCTAATCCCAGTTTG</p></td>
<td>Fish</td>
<td><p>Wilderlab in house</p>
<p>(Miya <em>et al</em>. 2015)</p></td>
</tr>
<tr class="even">
<td>RJ</td>
<td>mt12S</td>
<td><p>TTAGATACCCTACTATG</p>
<p>AAGCTAGCGCTTGTAGT</p></td>
<td>Sharks and rays</td>
<td><p>(Riaz <em>et al</em>. 2011) (M)</p>
<p>Wilderlab in house</p></td>
</tr>
<tr class="odd">
<td>BE</td>
<td>18S-V9</td>
<td><p>CCCTGCCHTTTGTACACAC</p>
<p>CCTTCYGCAGGTTCACCTAC</p></td>
<td>Eukaryotes</td>
<td>(Amaral-Zettler <em>et al</em>. 2009)</td>
</tr>
<tr class="even">
<td>BU</td>
<td>18S-V9</td>
<td><p>TTGTACACACCGCCC</p>
<p>CCTTCYGCAGGTTCACCTAC</p></td>
<td>Eukaryotes and bacteria</td>
<td>(Amaral-Zettler <em>et al</em>. 2009)</td>
</tr>
<tr class="odd">
<td>BX*</td>
<td>18S</td>
<td><p>GCCAGTAGTCATATGCTTGTCT</p>
<p>GCCTGCTGCCTTCCTT</p></td>
<td>General eukaryote</td>
<td>(Pochon <em>et al</em>. 2013)</td>
</tr>
<tr class="even">
<td>CI</td>
<td>COI</td>
<td><p>DACWGGWTGAACWGTWTAYCCHCC</p>
<p>GTTGTAATAAAATTAAYDGCYCCTARAATDGA</p></td>
<td>Invertebrates</td>
<td><p>(Leray <em>et al</em>. 2013) (M)</p>
<p>(Wilkinson <em>et al</em>. 2024)</p></td>
</tr>
<tr class="odd">
<td>GD*</td>
<td>ITS2</td>
<td><p>GARTCTTTGAACGCAAATGGC</p>
<p>GCTTATTAATATGCTTAAATTCAGCG</p></td>
<td>Coral</td>
<td>(Brian <em>et al</em>. 2019)</td>
</tr>
<tr class="even">
<td>HD*</td>
<td>mt16S</td>
<td><p>GGACGATAAGACCCTATAAA</p>
<p>ACGCTGTTATCCCTAAAGT</p></td>
<td>Crustaceans</td>
<td>(Komai <em>et al</em>. 2019)</td>
</tr>
<tr class="odd">
<td>UM</td>
<td>16S-V5</td>
<td><p>GGATTAGATACCCTGGTA</p>
<p>CCGTCAATTCMTTTRAGTTT</p></td>
<td>Bacteria</td>
<td>(Morey <em>et al</em>. 2006) (Lane <em>et al</em>. 1985)</td>
</tr>
<tr class="even">
<td>XN*</td>
<td>COI</td>
<td><p>DACWGGWTGAACWGTWTAYCCHCC</p>
<p>TANACYTCNGGRTGNCCRAARAAYCA</p></td>
<td>Invertebrates</td>
<td><p>(Leray <em>et al</em>. 2013) (M)</p>
<p>(Geller <em>et al</em>. 2013) (M)</p></td>
</tr>
</tbody>
</table>
