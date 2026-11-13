# Demonstration files

A small cut of CSIRO's SEA-MES eDNA data record, for trying the FAIRe tools app. The files come from
`demo/seames` and `dev/faire_mapper_seames` in this repository. **They are not data for ecological
analysis**; use the published record for that.

| File | What it is |
|---|---|
| `SEA-MES_10L_samples.csv` | The 13 10 L samples from file 1 of the record (the NCBI BioSample sheet), with the column *Negative control type* added, as a person following the mapper's guide would add it (`dev/faire_mapper_seames/prepare_table.py`) |
| `4_SEA-MES_16S_ASV_level_output_with_seq.csv` | The 16S fish ASV table, with sequences and preliminary taxonomy (written as otuRaw and taxaRaw) |
| `5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv` | The authors' curated fish taxa (written as otuFinal and taxaFinal) |
| `filereport_read_run_PRJNA1263580.tsv` | ENA's run report for these samples' libraries (the library table) |
| `methods.txt` | The methods from the project's NESP final report (for finding primers) |
| `SEA-MES_project_values_Fish16S.tsv` | Values for the whole project, as the trial gave them (`dev/faire_mapper_seames/project_values.tsv`), with otu_final_description changed to describe file 5 |
| `biosample_accessions.tsv`, `ena_sample_receipt.xml` | The samples' BioSample accessions and a stand-in ENA receipt, made from the run report by `dev/faire_mapper_seames/accessions.py`, as the samples are registered already |

## Source and licence

Deagle BE, Jayasinghe SA, Bessey C, Bodrossy L, West KM (2025). Environmental DNA data from the RV
Investigator South-East Australian Marine Ecosystem Survey (SEA-MES) voyages (IN2023_V05 and
IN2024_V03), version 2. CSIRO Data Access Portal, doi:10.25919/ngqx-3557. Licensed under CC BY 4.0.
Raw reads: NCBI BioProject PRJNA1263580. The methods text is from the project's NESP final report
(Deagle et al. 2025, CC BY 4.0). The changes made are listed above and in `demo/seames/README.md`.
