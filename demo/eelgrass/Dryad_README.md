# Data from: Applying eDNA Metabarcoding to assess invertebrate biodiversity of Eelgrass (Zostera marina) meadows across Nova Scotia

Dataset DOI: [10.5061/dryad.gqnk98t0c](10.5061/dryad.gqnk98t0c)

## Description of the data and file structure

# Marine invertebrate eDNA metabarcoding in Eelgrass Meadows Across Nova Scotia, Canada

## Contact Information

Corresponding author: [Nick.Jeffery@dfo-mpo.gc.ca](mailto:Nick.Jeffery@dfo-mpo.gc.ca)

Address: Bedford Institute of Oceanography, Dartmouth, Nova Scotia, Canada, B2Y 4A2

Project led by: Courtney Trask, Cape Breton University

Submitted to Canadian Journal of Fisheries and Aquatic Sciences

Alternate Contact: [Timothy_Rawlings@cbu.ca](mailto:Timothy_Rawlings@cbu.ca) 

### Dataset Overview

The data files included her consist of data from eDNA metabarcoding samples from 17 locations across coastal Nova Scotia, sampled in 2019 and 2023. Included are an amplicon sequence variant (ASV) table for all samples, arranged as a matrix of the species detected with the number of sequence reads per site and sample. The ASV table was generated through the QIIME2 pipeline, where COI primers were trimmed and sequences merged and denoised in DADA2 (Callahan et al. 2016). Also included are two .fasta files which include the representative DNA sequences for each ASV detected from samples in 2019 and 2023. We also compare eDNA ASV results with species detected in coastal eelgrass meadows in Nova Scotia using 'traditional' methods, including sediment coring, snorkeling, and net-based methods. 

###### Date Range

Samples for 10 sites were collected between July and September 2019, while samples collected in Cape Breton were sampled between June and August 2023. 

###### eDNA Marker

All samples were analyzed for a fragment of the COI gene amplified by the Leray et al. (2013) primer set.

### References

Callahan, B. J., McMurdie, P. J., Rosen, M. J., Han, A. W., Johnson, A. J. A., & Holmes, S. P. (2016). DADA2: High-resolution sample inference from Illumina amplicon data. *Nature methods*, *13*(7), 581-583.

Leray M., Yang J. Y., Meyer C. P., Mills S. C., Agudelo N., Ranwez V., et al. (2013). A new versatile primer set targeting a short fragment of the mitochondrial COI region for metabarcoding metazoan diversity: application for characterizing coral reef fish gut contents. *Front. Zoology* 10 (1), 34. doi: 10.1186/1742-9994-10-34

### Files and variables

#### File: Final_ASVTable_withTaxonomy_Filtered.csv

**Description:** A table of all amplicon sequence variants (ASVs) and associated taxonomy (species names) with read counts per taxon per sample. 

##### Variables

* Phylum: The invertebrate phylum of the species listed
* Class: The class of the species listed
* Species: The species and genus name associated with a given ASV.
* Probability: The probability (up to 100%) that the given species name belongs to the associated ASV
* CAB-1: Sample replicate 1 from Cable Island site
* CAB-2: Sample replicate 2 from Cable Island site
* CAB-3: Sample replicate 3 from Cable Island site
* CON-1: Sample replicate 1 from Conrods Beach
* CON-2: Sample replicate 2 from Conrods Beach
* CON-3: Sample replicate 3 from Conrods Beach
* FAI-1: Sample replicate 1 from Fifty Acre Island
* FAI-2: Sample replicate 2 from Fifty Acre Island
* FAI-3: Sample replicate 3 from Fifty Acre Island
* FRK-1: Sample replicate 1 from Franks George Island
* FRK-2: Sample replicate 2 from Franks George Island
* FRK-3: Sample replicate 3 from Franks George Island
* MOS-1: Sample replicate 1 from Moosehead
* MOS-2: Sample replicate 2 from Moosehead
* MOS-3: Sample replicate 3 from Moosehead
* PLS-1: Sample replicate 1 from Pleasant Point
* PLS-2: Sample replicate 2 from Pleasant Point
* PLS-3: Sample replicate 3 from Pleasant Point
* RSE-1: Sample replicate 1 from Rose Bay
* RSE-2: Sample replicate 2 from Rose Bay
* TAE-1: Sample replicate 1 from Taylor Head East
* TAE-2: Sample replicate 2 from Taylor Head East
* TAE-3: Sample replicate 3 from Taylor Head East
* TAW-1: Sample replicate 1 from Taylor Head West
* TAW-2: Sample replicate 2 from Taylor Head West
* TAW-3: Sample replicate 3 from Taylor Head West
* WRK02-1: Sample replicate 1 from Wreck Cove
* WRK02-2: Sample replicate 2 from Wreck Cove
* WRK02-3: Sample replicate 3 from Wreck Cove
* ASB-1: Sample replicate 1 from Aspy Bay
* ASB-2: Sample replicate 2 from Aspy Bay
* ASB-3: Sample replicate 3 from Aspy Bay
* CHB-1: Sample replicate 1 from Chebogue
* CHB-2: Sample replicate 2 from Chebogue
* CHB-3: Sample replicate 3 from Chebogue
* LIN-1: Sample replicate 1 from Lingan Bay
* LIN-2: Sample replicate 2 from Lingan Bay
* LIN-3: Sample replicate 3 from Lingan Bay
* MIR-1: Sample replicate 1 from Mira River
* MIR-2: Sample replicate 2 from Mira River
* MIR-3: Sample replicate 3 from Mira River
* CHT-1: Sample replicate 1 from Cheticamp
* CHT-2: Sample replicate 2 from Cheticamp
* CHT-3: Sample replicate 3 from Cheticamp
* NOR-1: Sample replicate 1 from North River
* NOR-2: Sample replicate 2 from North River
* NOR-3: Sample replicate 3 from North River
* ESB-1: Sample replicate 1 from East Bay
* ESB-2: Sample replicate 2 from East Bay
* ESB-3: Sample replicate 3 from East Bay

#### File: Site_coordinates.csv

**Description:** A csv file with the GPS coordinates in WGS84 decimal degree format for each sample site

##### Variables

* Site: The name of the sampling site
* Latitude: The latitude of the sampling site in decimal degrees
* Longitude: The longitude of the sampling site in decimal degrees
* Code: A short code representing the sampling site name

#### File: 2023_ASV_dna-sequences.fasta

**Description:** A fasta file of representative DNA sequences of all amplicon sequence variants from the 2023 samples

#### File: CO1_2019samples_9205ASVs_dna-sequences.fasta

**Description:** A fasta file of representative DNA sequences of all amplicon sequence variants from the 2019 samples

#### File: comp_data_raw.csv

**Description:** A csv file with taxa used for analysis in the manuscript. It contains the taxonomic ranks per species, any taxonomic issues noted (e.g., an outdated species name being used by a database), and whether it was detected by 'traditional' methods (net-based capture, snorkeling, or sediment cores), or by eDNA metabarcoding.

##### Variables

* Species: The species name 
* Taxonomic issues: Any taxonomic issues when comparing species between previous publications and the eDNA metabarcoding data. These could include an outdated species or genus name being used in either the 'traditional' or eDNA taxonomic information. 
* Phylum: The phylum of the species in question
* Subphylum/Class: The subphylum/class of the species in question
* Order: The order of the species in question
* Family: The family of the species in question
* Traditional: Whether the species was detected in previous publications using 'traditional' methods, including net-based capture, snorkeling, or sediment cores
* eDNA: whether the species was detected in eDNA data from 2019 and/or 2023 by Trask et al. 

## Code/software

All raw eDNA fastq files were first analyzed with FastQC for quality checking, followed by the QIIME2 2024.5-amplicon version pipeline. All code for bioinformatics and analyses in R are available at [https://github.com/dfo-mar-mpas/coastal-invertebrate-metabarcoding](https://github.com/dfo-mar-mpas/coastal-invertebrate-metabarcoding). 

The workflow for analyzing these data is as follows: 

1\) FastQC - DNA sequence quality control 

2\) Import into QIIME2 (2024.5-amplicon version)

3\) Remove forward and reverse COI primers with QIIME2 cutadapt plugin

4\) Denoise and merge sequences in QIIME2 dada2 plugin. An ASV table is produced at this step.

5\) Use COI RDP-classifier v5.0.0 to assign taxonomy to representative sequences for each ASV. 

6\) In R 4.4.0, merge sample ASV table and taxonomy assignments for ecological analyses. 

7\) R package *vegan* was primarily used to investigate species diversity and community structure (specaccum and nmds functions). 

8\) All plots created using ggplot2 in R 4.4.0

## Access information

Other publicly accessible locations of the data:

* Raw fastq files are available in NCBI **PRJNA1145319**
* These data files will also be made available on the Government of Canada Open Data Platform

